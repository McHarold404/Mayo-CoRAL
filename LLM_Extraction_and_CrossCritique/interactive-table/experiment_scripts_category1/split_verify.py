#!/usr/bin/env python

"""
split_verify.py

Pipeline 3 — Three-stage selection (single run per question) using vLLM, with batching:

  Stage 1: choose the appropriate FILTERS (categories + values)
  Stage 2: choose the appropriate COLUMNS
  Stage 3: re-evaluate filters + columns together; accept or revise

- Uses the same directory layout and CLI as base_prompt.py
- Canonicalizes filter NAMES to your interface terms (e.g., "ICI Class", "Clinical Setting", etc.).
- Canonicalizes common filter VALUE synonyms (e.g., PD1 -> PD-1, NSCLC -> Non-Small Cell Lung Cancer (NSCLC), 2L -> Second-line+).
- Enforces REQUIRED_COLS and cap on additional columns.
- Writes one row per question per model into results/split_verify/*.xlsx
- Supports --mode run / --mode eval with exact-match evaluation vs Ground Truth JSON.
- Uses batched vLLM calls for much faster processing.
"""

import os
import re
import gc
import sys
import json
import ast
import time
import argparse
from datetime import datetime

import torch
import pandas as pd
from dotenv import load_dotenv
from vllm import LLM, SamplingParams

# ============================
# CONFIGURATION
# ============================

load_dotenv()

BASE_DIR = "/mnt/data1/srchowd3/Mayo-CoRAL/LLM_Extraction_and_CrossCritique/interactive-table"
INPUT_FILE = f"{BASE_DIR}/runs/query-chosen-filters-columns - full.xlsx"
RESULTS_DIR = f"{BASE_DIR}/results"

# one subfolder for this script inside results/
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
EXPERIMENT_RESULTS_DIR = os.path.join(RESULTS_DIR, SCRIPT_NAME)

DEF_FOLDER = f"{BASE_DIR}/definitions_folder"
FILTER_NAMES_PATH = f"{DEF_FOLDER}/definitions - aim2 - filter names.txt"
COLUMN_DEFS_PATH  = f"{DEF_FOLDER}/definitions - aim2 - column.txt"
FILTER_DEFS_FULL_PATH = f"{DEF_FOLDER}/definitions - aim2 - filter.txt"

# Ground truth JSON column (same as base_prompt)
GT_FILTER_COL = "Ground Truth JSON"
GT_COLUMN_COL = "Ground Truth JSON"

# HF / vLLM
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    sys.exit("❌ Error: HF_TOKEN not found in .env file or environment variables.")

DEFAULT_MODEL_ID = os.getenv("MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.2")

REQUIRED_COLS = ["NCT", "PMID", "Authors", "Year"]
MAX_ADDITIONAL_COLS = 6  # additional columns on top of REQUIRED_COLS

# Batching for speed
BATCH_SIZE = 32  # tune: 8, 16, 32, 64 depending on GPU memory

# Environment for HF cache
os.environ["HF_TOKEN"] = HF_TOKEN
if not os.environ.get("HF_HOME"):
    os.environ["HF_HOME"] = "/scratch/srchowd3/models"

# ============================
# LOAD DEFINITIONS
# ============================

def load_definitions():
    print("Loading definition files...")
    try:
        with open(FILTER_NAMES_PATH, "r", encoding="utf-8") as f:
            filter_names = f.read()
        with open(COLUMN_DEFS_PATH, "r", encoding="utf-8") as f:
            column_defs = f.read()
        with open(FILTER_DEFS_FULL_PATH, "r", encoding="utf-8") as f:
            filter_defs = f.read()
        return filter_names, column_defs, filter_defs
    except FileNotFoundError as e:
        print(f"CRITICAL ERROR: Could not find definition files.\n{e}")
        sys.exit(1)

FILTER_NAMES_TEXT, COLUMN_DEFS_TEXT, FILTER_DEFS_TEXT = load_definitions()

# ============================
# JSON + PARSING HELPERS
# ============================

def strip_code_fences(s: str) -> str:
    s = str(s or "").strip()
    if s.startswith("```") and s.endswith("```"):
        s = s.strip("`")
        s = "\n".join(s.splitlines()[1:])
    return s.strip()

def extract_json(text: str):
    """
    Robust JSON extraction:
    - Try direct json.loads
    - Then try first {...} block
    - Then ast.literal_eval as fallback
    Raises ValueError if nothing works.
    """
    raw = strip_code_fences(text or "")

    # 1) direct
    try:
        return json.loads(raw)
    except Exception:
        pass

    # 2) first {...}
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = raw[start:end+1]
            try:
                return json.loads(candidate)
            except Exception:
                try:
                    obj = ast.literal_eval(candidate)
                    if isinstance(obj, (dict, list)):
                        return obj
                except Exception:
                    pass
    except Exception:
        pass

    raise ValueError(f"Could not parse JSON from model text: {raw[:200]}...")

def parse_json_safe(text):
    """Return dict/list or None on failure."""
    if isinstance(text, (dict, list)):
        return text
    try:
        return extract_json(text)
    except Exception:
        return None

# ============================
# CANONICALIZATION (filter NAMES & VALUES)
# ============================

CANON_KEYS = {
    # Target interface names
    "ICI Class": "ICI Class",
    "ICI Name": "ICI Name",
    "Cancer Type": "Cancer Type",
    "Type of Therapy": "Type of Therapy",
    "Type of combination (Treatment Arm)": "Type of combination (Treatment Arm)",
    "Control Arm": "Control Arm",
    "Clinical Setting": "Clinical Setting",
    "Trial Phase": "Trial Phase",
    "Type of Study": "Type of Study",
    "Primary Endpoint": "Primary Endpoint",
    "Included in MA": "Included in MA",

    # Older / synonyms → canonical
    "Class of ICI": "ICI Class",
    "Name of ICI": "ICI Name",
    "Cancer type": "Cancer Type",
    "Monotherapy/combination": "Type of Therapy",
    "Monotherapy/Combination": "Type of Therapy",
    "Monotherapy vs Combination": "Type of Therapy",
    "Mono/Combo": "Type of Therapy",
    "Type of combination": "Type of combination (Treatment Arm)",
    "Type of combination (Treatment Arm)": "Type of combination (Treatment Arm)",
    "Type of control": "Control Arm",
    "Control regimen": "Control Arm",
    "Trial phase": "Trial Phase",
    "Clinical Trial Phase": "Trial Phase",
    "Phase": "Trial Phase",
    "Clinical setting in relation to surgery": "Clinical Setting",
    "Clinical Setting (Perioperative)": "Clinical Setting",
    "Clinical setting": "Clinical Setting",
    "Perioperative setting": "Clinical Setting",
    "Setting in relation to surgery": "Clinical Setting",
    "Primary endpoint": "Primary Endpoint",
    "Primary Endpoint(s)": "Primary Endpoint",
    "Primary endpoints": "Primary Endpoint",
    "Included in Meta-analysis": "Included in MA",
    "Lines of treatment": "Clinical Setting",  # will be converted to setting values
}

def _canon_simple(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())

ICI_CLASS_VALUE_MAP = {
    "pd1": "PD-1",
    "pd-1": "PD-1",
    "pd 1": "PD-1",
    "pd_l1": "PD-L1",
    "pdl1": "PD-L1",
    "pd-l1": "PD-L1",
    "pd l1": "PD-L1",
    "ctla4": "CTLA-4",
    "ctla-4": "CTLA-4",
    "ctla 4": "CTLA-4",
}

TYPE_OF_THERAPY_VALUE_MAP = {
    "monotherapy": "Monotherapy",
    "mono": "Monotherapy",
    "combination": "Combination",
    "combination therapy": "Combination",
}

PRIMARY_ENDPOINT_VALUE_MAP = {
    "os (overall survival)": "OS",
    "os": "OS",
    "pfs": "PFS",
    "orr": "ORR",
    "rfs": "RFS",
    "dfs": "RFS",
    "efs": "EFS",
    "pcr": "Path CR",
    "path cr": "Path CR",
    "safety": "Safety",
}

TRIAL_PHASE_VALUE_MAP = {
    "iii": "Phase 3",
    "phase iii": "Phase 3",
    "3": "Phase 3",
    "ii": "Phase 2",
    "phase ii": "Phase 2",
    "2": "Phase 2",
}

TYPE_OF_STUDY_VALUE_MAP = {
    "original": "Original publication",
    "original publication": "Original publication",
    "follow-up": "Follow-up",
    "follow up": "Follow-up",
}

INCLUDED_MA_VALUE_MAP = {
    "yes": "Yes",
    "no": "No",
}

COMBO_TREATMENT_VALUE_MAP = {
    "ici + meki (mek inhibitor)": "ICI + MEKi",
    "ici + meki": "ICI + MEKi",
    "ici + radiation": "ICI + Radiation",
    "ici + radiotherapy": "ICI + Radiation",
    "ici + vaccine": "ICI + Vaccine",
    "ici + tki": "ICI + TKI",
    "ici + chemo": "ICI + Chemo",
    "ici + anti-vegf": "ICI + Anti-VEGF",
    "ici + brafi + meki": "ICI + BRAFi + MEKi",
    "ici + chemo + anti-vegf": "ICI + Chemo + Anti-VEGF",
    "ici + ici": "ICI + ICI",
    "ici + ici + chemo": "ICI + ICI + Chemo",
}

CONTROL_ARM_VALUE_MAP = {
    "chemo": "Chemo",
    "tki": "TKI",
    "interferon": "Interferon",
    "multikinase inhibitor": "Multikinase inhibitor",
    "mtor inhibitor": "mTOR inhibitor",
    "radiation": "Radiation",
    "vaccine": "Vaccine",
    "placebo": "Placebo",
    "best supportive care": "Best Supportive Care",
    "bsc": "Best Supportive Care",
    "chemo / anti-egfr": "Chemo / Anti-EGFR",
    "chemo / anti-vegf": "Chemo / Anti-VEGF",
    "chemo / tki": "Chemo / TKI",
    "brafi + meki": "BRAFi + MEKi",
}

CANCER_TYPE_VALUE_MAP = {
    "nsclc": "Non-Small Cell Lung Cancer (NSCLC)",
    "non-small cell lung cancer": "Non-Small Cell Lung Cancer (NSCLC)",
    "non small cell lung cancer": "Non-Small Cell Lung Cancer (NSCLC)",
    "sclc": "Small Cell Lung Cancer (SCLC)",
    "small cell lung cancer": "Small Cell Lung Cancer (SCLC)",
    "hnscc": "Head and Neck (HNSCC)",
    "head and neck": "Head and Neck",
    "head and neck (hnscc)": "Head and Neck (HNSCC)",
    "hcc": "Hepatocellular carcinoma (HCC)",
    "hepatocellular carcinoma": "Hepatocellular carcinoma (HCC)",
    "rcc": "Renal Cell Carcinoma (RCC)",
    "renal cell carcinoma": "Renal Cell Carcinoma (RCC)",
    "melanoma": "Melanoma",
    "breast": "Breast",
    "colorectal": "Colorectal",
    "gastric/gej": "Gastric/GEJ",
    "esophageal/gej": "Esophageal/GEJ",
    "urothelial": "Urothelial and Bladder",
    "bladder": "Bladder",
    "renal cell": "Renal Cell Carcinoma (RCC)",
    "non-small cell lung cancer (nsclc)": "Non-Small Cell Lung Cancer (NSCLC)",
    "small cell lung cancer (sclc)": "Small Cell Lung Cancer (SCLC)",
}

def _canon_clinical_setting(raw_value: str) -> str:
    v = _canon_simple(raw_value).lower()
    if v in {
        "neoadjuvant",
        "adjuvant",
        "perioperative",
        "maintenance",
        "metastatic / recurrent (unresectable)",
    }:
        if v == "metastatic / recurrent (unresectable)":
            return "Metastatic / Recurrent (Unresectable)"
        return v.title()
    if v in {"first-line", "first line", "1l"}:
        return "First-line metastatic"
    if v in {"second-line", "second line", "2l", "2l+", "second-line+"}:
        return "Second-line+"
    if v in {"third-line", "third line", "3l"}:
        return "Second-line+"
    if "second-line" in v or "2l" in v:
        return "Second-line+"
    if "first-line" in v or "1l" in v:
        return "First-line metastatic"
    return raw_value

def canonicalize_key(k: str) -> str:
    k = str(k or "").strip()
    return CANON_KEYS.get(k, k)

def canonicalize_value(cat: str, value: str) -> str:
    cat_c = canonicalize_key(cat)
    v = _canon_simple(value)
    low = v.lower()

    if cat_c == "ICI Class":
        return ICI_CLASS_VALUE_MAP.get(low, v)
    if cat_c == "Type of Therapy":
        return TYPE_OF_THERAPY_VALUE_MAP.get(low, v)
    if cat_c == "Primary Endpoint":
        return PRIMARY_ENDPOINT_VALUE_MAP.get(low, v)
    if cat_c == "Trial Phase":
        return TRIAL_PHASE_VALUE_MAP.get(low, v)
    if cat_c == "Type of Study":
        return TYPE_OF_STUDY_VALUE_MAP.get(low, v)
    if cat_c == "Included in MA":
        return INCLUDED_MA_VALUE_MAP.get(low, v)
    if cat_c == "Type of combination (Treatment Arm)":
        return COMBO_TREATMENT_VALUE_MAP.get(low, v)
    if cat_c == "Control Arm":
        return CONTROL_ARM_VALUE_MAP.get(low, v)
    if cat_c == "Cancer Type":
        return CANCER_TYPE_VALUE_MAP.get(low, v)
    if cat_c == "Clinical Setting":
        return _canon_clinical_setting(v)
    return v

def normalize_selected_filter(sel: dict) -> dict:
    """
    - Canonicalize keys to interface terms
    - Drop empty / "All"
    - Canonicalize values per-category
    - Fold "Lines of treatment" into Clinical Setting values
    """
    out = {}
    for k, v in (sel or {}).items():
        if v is None:
            continue
        vs = str(v).strip()
        if not vs or vs.lower() == "all":
            continue

        k_can = canonicalize_key(k)
        if k in ("Lines of treatment",) and k_can == "Clinical Setting":
            vs = _canon_clinical_setting(vs)

        out[k_can] = canonicalize_value(k_can, vs)
    return out

# ============================
# COLUMN NORMALIZATION
# ============================

def _ordered_values_from_column_object(col_obj: dict) -> list[str]:
    if not isinstance(col_obj, dict):
        return []
    items = []
    for k, v in col_obj.items():
        m = re.search(r"Column\s*(\d+)", str(k))
        idx = int(m.group(1)) if m else 10**9
        items.append((idx, v))
    items.sort(key=lambda x: x[0])
    return [val for _, val in items if isinstance(val, str) and val.strip()]

def normalize_selected_column(selected_column) -> dict:
    """
    Ensure REQUIRED_COLS first, dedupe, cap to REQUIRED + MAX_ADDITIONAL_COLS,
    then enumerate as {"Column 1": "...", ...}
    """
    if isinstance(selected_column, dict):
        cols = _ordered_values_from_column_object(selected_column)
    elif isinstance(selected_column, list):
        cols = [c for c in selected_column if isinstance(c, str) and c.strip()]
    else:
        cols = []

    out_list, seen = [], set()
    for rc in REQUIRED_COLS:
        if rc not in seen:
            out_list.append(rc); seen.add(rc)
    for c in cols:
        if c not in seen:
            out_list.append(c); seen.add(c)

    cap = len(REQUIRED_COLS) + MAX_ADDITIONAL_COLS
    out_list = out_list[:cap]
    return {f"Column {i+1}": name for i, name in enumerate(out_list)}

# ============================
# PROMPT BUILDERS (3 STAGES)
# ============================

def build_stage1_prompt(question: str) -> str:
    schema = (
        '{\n'
        '  "selected_filter": {\n'
        '    "Canonical Filter Name 1": "Value",\n'
        '    "Canonical Filter Name 2": "Value"\n'
        '  }\n'
        '}'
    )
    example = '{"selected_filter":{"Cancer Type":"Non-Small Cell Lung Cancer (NSCLC)","Trial Phase":"Phase 3"}}'
    return (
        "You are a medical expert researching cancer.\n"
        "Stage 1: Select ONLY the filters (categories + values) relevant to the question.\n"
        "Return ONLY a valid JSON object with key `selected_filter` (no prose, no code fences):\n"
        f"{schema}\n\n"
        "Rules:\n"
        "- Use double quotes everywhere.\n"
        "- Use these canonical category names whenever possible (map synonyms to them):\n"
        '  [\"ICI Class\",\"ICI Name\",\"Cancer Type\",\"Type of Therapy\",'
        '\"Type of combination (Treatment Arm)\",\"Control Arm\",\"Clinical Setting\",'
        '\"Trial Phase\",\"Type of Study\",\"Primary Endpoint\",\"Included in MA\"]\n'
        "- Use exact strings for values from the filter definitions when applicable.\n"
        "- Omit any filters whose correct value would be \"All\".\n"
        "- Include only filters directly justified by the question.\n\n"
        "Available filter CATEGORY NAMES (reference):\n"
        f"{FILTER_NAMES_TEXT}\n\n"
        "Available filter CATEGORIES + VALUES (use exact strings whenever possible):\n"
        f"{FILTER_DEFS_TEXT}\n\n"
        f"Question: {question}\n"
        "Return JSON now.\n"
        f"Example (not prescriptive): {example}"
    )

def build_stage2_prompt(question: str, selected_filter: dict) -> str:
    total_slots = len(REQUIRED_COLS) + MAX_ADDITIONAL_COLS
    schema_columns = ',\n'.join(
        [f'    "Column {i}": "Column Name"' for i in range(1, total_slots + 1)]
    )
    schema = '{\n  "selected_column": {\n' + schema_columns + '\n  }\n}'

    return (
        "You are a medical expert researching cancer.\n"
        "Stage 2: Select the OUTPUT COLUMNS for the table.\n"
        f"- These columns are ALWAYS included: {', '.join(REQUIRED_COLS)}.\n"
        f"- You may add up to {MAX_ADDITIONAL_COLS} additional columns.\n\n"
        "Return ONLY a valid JSON object with key `selected_column` (no prose, no code fences):\n"
        f"{schema}\n\n"
        "Rules:\n"
        "- Use double quotes everywhere.\n"
        f"- Ensure {', '.join(REQUIRED_COLS)} are included.\n"
        f"- Choose at most {MAX_ADDITIONAL_COLS} additional columns, justified by the question.\n"
        "- Use exact column names from the list provided below.\n\n"
        "Context — currently chosen filters (use them to guide column selection):\n"
        f"{json.dumps(selected_filter, ensure_ascii=False)}\n\n"
        "Available columns and definitions (select by exact name):\n"
        f"{COLUMN_DEFS_TEXT}\n\n"
        f"Question: {question}\n"
        "Return JSON now."
    )

def build_stage3_prompt(question: str, selected_filter: dict, selected_column_obj: dict) -> str:
    return (
        "You are a medical expert researching cancer.\n"
        "Stage 3: Final JOINT sanity check of filters + columns.\n"
        "If everything is consistent and minimal, return status \"accept\".\n"
        "Otherwise, return status \"revise\" with improved filters and/or columns.\n\n"
        "Return ONLY one valid JSON object (no prose, no code fences) with one of these schemas:\n"
        '{ "status":"accept","selected_filter":{...},"selected_column":{...} }\n'
        '{ "status":"revise","selected_filter":{...},"selected_column":{...},"notes":"<25 chars>" }\n\n'
        "Rules:\n"
        "- Filters must use canonical category names (map synonyms to: "
        '\"ICI Class\",\"ICI Name\",\"Cancer Type\",\"Type of Therapy\",'
        '\"Type of combination (Treatment Arm)\",\"Control Arm\",\"Clinical Setting\",'
        '\"Trial Phase\",\"Type of Study\",\"Primary Endpoint\",\"Included in MA\").\n'
        f"- Columns must include {', '.join(REQUIRED_COLS)} and only up to {MAX_ADDITIONAL_COLS} extras.\n"
        "- Omit any filter whose correct value would be \"All\".\n"
        "- Prefer a minimal set that fully answers the question; drop irrelevant columns.\n\n"
        "Current selection to evaluate:\n"
        f"Question: {question}\n"
        f"Filters: {json.dumps(selected_filter, ensure_ascii=False)}\n"
        f"Columns: {json.dumps(selected_column_obj, ensure_ascii=False)}\n"
        "Return JSON now."
    )

# ============================
# RESUME LOGIC (same pattern as base_prompt)
# ============================

def get_processed_indices_for_model(model_id: str):
    """
    Collect all Original_Index values that were already processed for this model,
    based on files in results/split_verify/ with prefix <model_name>_.
    """
    os.makedirs(EXPERIMENT_RESULTS_DIR, exist_ok=True)

    safe_name = model_id.split("/")[-1]
    processed = set()

    if os.path.isdir(EXPERIMENT_RESULTS_DIR):
        for fname in os.listdir(EXPERIMENT_RESULTS_DIR):
            if not fname.endswith(".xlsx"):
                continue
            if not fname.startswith(safe_name + "_"):
                continue

            fpath = os.path.join(EXPERIMENT_RESULTS_DIR, fname)
            try:
                df_res = pd.read_excel(fpath)
                if "Original_Index" in df_res.columns:
                    processed.update(
                        df_res["Original_Index"].dropna().astype(int).tolist()
                    )
            except Exception as e:
                print(f"⚠️ Could not read results file {fname}: {e}")

    print(f"📂 Found {len(processed)} processed rows for model '{model_id}' in {EXPERIMENT_RESULTS_DIR}.")
    return processed

def load_all_results_for_model(model_id: str) -> pd.DataFrame | None:
    """Load and concatenate all result files for this script for a given model."""
    os.makedirs(EXPERIMENT_RESULTS_DIR, exist_ok=True)
    safe_name = model_id.split("/")[-1]

    frames = []
    for fname in os.listdir(EXPERIMENT_RESULTS_DIR):
        if not fname.endswith(".xlsx"):
            continue
        if not fname.startswith(safe_name + "_"):
            continue

        fpath = os.path.join(EXPERIMENT_RESULTS_DIR, fname)
        try:
            frames.append(pd.read_excel(fpath))
        except Exception as e:
            print(f"⚠️ Could not read results file {fname}: {e}")

    if not frames:
        print(f"❌ No result files found for model '{model_id}' in {EXPERIMENT_RESULTS_DIR}")
        return None

    df_all = pd.concat(frames, ignore_index=True)

    if "Original_Index" in df_all.columns:
        df_all = df_all.dropna(subset=["Original_Index"])
        df_all["Original_Index"] = df_all["Original_Index"].astype(int)
        df_all = (
            df_all
            .sort_index()
            .drop_duplicates(subset=["Original_Index"], keep="last")
        )

    return df_all

# ============================
# EVAL HELPERS (exact match vs GT)
# ============================

def precision_recall(pred_set, true_set):
    """
    Compute precision and recall between two sets.
    - If both empty -> (1.0, 1.0)
    - If pred empty, true non-empty -> (0.0, 0.0)
    - If true empty, pred non-empty -> (0.0, 0.0)
    """
    pred = set(pred_set)
    true = set(true_set)

    if not pred and not true:
        return 1.0, 1.0

    tp = len(pred & true)
    precision = tp / len(pred) if pred else 0.0
    recall    = tp / len(true) if true else 0.0

    return precision, recall

def evaluate_model_exact_match(model_id: str):
    """
    For a given model, compute FILTER and COLUMN precision/recall vs ground truth.

    Filters:
      - Items = (category, value) pairs (after canonicalization).
    Columns:
      - Items = column names (ignoring "Column i" positions).

    Uses Original_Index to align model outputs with INPUT_FILE rows.
    """
    print(f"\n🔍 Starting evaluation for model (split_verify): {model_id}")

    pred_df = load_all_results_for_model(model_id)
    if pred_df is None or pred_df.empty:
        print("❌ No predictions to evaluate.")
        return

    full_df = pd.read_excel(INPUT_FILE)

    if GT_FILTER_COL not in full_df.columns or GT_COLUMN_COL not in full_df.columns:
        print(
            f"❌ Ground truth columns '{GT_FILTER_COL}' and/or '{GT_COLUMN_COL}' "
            f"not found in {INPUT_FILE}. Please update GT_FILTER_COL / GT_COLUMN_COL."
        )
        return

    records = []
    n = 0

    sum_prec_filters = 0.0
    sum_rec_filters  = 0.0
    sum_prec_cols    = 0.0
    sum_rec_cols     = 0.0

    for _, row in pred_df.iterrows():
        idx = int(row["Original_Index"])
        if idx not in full_df.index:
            print(f"⚠️ Original_Index {idx} not in ground truth file; skipping.")
            continue

        gt_row = full_df.loc[idx]

        # predictions (parsed JSON from our columns)
        pred_filter_obj = parse_json_safe(row.get("Parsed_Filter", "{}")) or {}
        pred_cols_obj   = parse_json_safe(row.get("Parsed_Column", "{}")) or {}

        # ground truth – expects an object like {"selected_filter": {...}, "selected_column": {...}}
        gt_obj = parse_json_safe(gt_row.get(GT_FILTER_COL, "{}")) or {}
        if isinstance(gt_obj, dict):
            gt_filter_raw = gt_obj.get("selected_filter", {})
            gt_cols_raw   = gt_obj.get("selected_column", {})
        else:
            gt_filter_raw = {}
            gt_cols_raw   = {}

        # Canonicalize both sides
        pred_filter_norm = normalize_selected_filter(pred_filter_obj or {})
        gt_filter_norm   = normalize_selected_filter(gt_filter_raw or {})

        pred_cols_norm = normalize_selected_column(pred_cols_obj or {})
        gt_cols_norm   = normalize_selected_column(gt_cols_raw or {})

        # Filters set: (category, value)
        pred_filter_items = set(pred_filter_norm.items())
        gt_filter_items   = set(gt_filter_norm.items())

        # Columns set: column names only
        pred_col_names = set(pred_cols_norm.values())
        gt_col_names   = set(gt_cols_norm.values())

        # Metrics
        prec_f, rec_f = precision_recall(pred_filter_items, gt_filter_items)
        prec_c, rec_c = precision_recall(pred_col_names, gt_col_names)

        n += 1
        sum_prec_filters += prec_f
        sum_rec_filters  += rec_f
        sum_prec_cols    += prec_c
        sum_rec_cols     += rec_c

        records.append({
            "Original_Index": idx,
            "Query": row.get("Query"),
            "Pred_Filter": json.dumps(pred_filter_norm, ensure_ascii=False),
            "GT_Filter":   json.dumps(gt_filter_norm, ensure_ascii=False),
            "Pred_Columns": json.dumps(pred_cols_norm, ensure_ascii=False),
            "GT_Columns":   json.dumps(gt_cols_norm, ensure_ascii=False),
            "precision_filters": prec_f,
            "recall_filters": rec_f,
            "precision_columns": prec_c,
            "recall_columns": rec_c,
        })

    if n == 0:
        print("⚠️ No aligned rows between predictions and ground truth.")
        return

    avg_prec_filters = sum_prec_filters / n
    avg_rec_filters  = sum_rec_filters  / n
    avg_prec_cols    = sum_prec_cols    / n
    avg_rec_cols     = sum_rec_cols     / n

    print("\n📊 Precision / Recall (averaged across rows)")
    print(f"  # evaluated rows               : {n}")
    print(f"  Filters - precision (avg)      : {avg_prec_filters:.3f}")
    print(f"  Filters - recall (avg)         : {avg_rec_filters:.3f}")
    print(f"  Columns - precision (avg)      : {avg_prec_cols:.3f}")
    print(f"  Columns - recall (avg)         : {avg_rec_cols:.3f}")

    eval_df = pd.DataFrame(records)
    os.makedirs(EXPERIMENT_RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    clean_model_name = model_id.split("/")[-1]
    eval_filename = os.path.join(
        EXPERIMENT_RESULTS_DIR,
        f"{clean_model_name}_EVAL_{timestamp}.xlsx"
    )
    eval_df.to_excel(eval_filename, index=False)
    print(f"\n✅ Per-row evaluation saved to: {eval_filename}\n")

# ============================
# SMALL UTILS
# ============================

def chunked(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

# ============================
# MAIN
# ============================

def main():
    parser = argparse.ArgumentParser()
        # vLLM memory utilization (default from .env: GPU_MEMORY_UTILIZATION)
    default_gpu_mem_util = float(os.getenv("GPU_MEMORY_UTILIZATION", "0.50"))
    parser.add_argument(
        "--gpu-mem-util",
        type=float,
        default=default_gpu_mem_util,
        help="vLLM gpu_memory_utilization (overrides .env GPU_MEMORY_UTILIZATION)."
    )
    
    
    parser.add_argument(
        "--mode",
        choices=["run", "eval"],
        default="run",
        help="'run' = generate with LLM, 'eval' = compute exact-match scores only."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Maximum number of NEW (unprocessed) rows to run. -1 = all remaining."
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="(Deprecated when resume is used) starting row index (ignored if resume)."
    )
    parser.add_argument("--tp", type=int, default=torch.cuda.device_count())
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL_ID)

    args = parser.parse_args()

    # Validate gpu memory utilization
    if not (0.0 < args.gpu_mem_util <= 1.0):
        raise ValueError(f"--gpu-mem-util must be in (0, 1]. Got {args.gpu_mem_util}")

    model_id = args.model.strip().rstrip(",")

    # ---- EVAL-ONLY ----
    if args.mode == "eval":
        evaluate_model_exact_match(model_id)
        return

    # ---- RUN / GENERATION ----
    print("\n--- HARDWARE CHECK ---")
    print("Torch:", torch.__version__)
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
    else:
        sys.exit("❌ CUDA not available.")
    print("----------------------\n")

    if args.tp > torch.cuda.device_count():
        args.tp = torch.cuda.device_count()

    if "mistral" in model_id.lower():
        tokenizer_mode = "mistral"
    else:
        tokenizer_mode = "auto"

    print(f"🚀 Initializing vLLM with model: {model_id}")
    print("⚠️  Config: Memory Util=0.5, Eager Mode=TRUE")
    print(f"🔤 tokenizer_mode = {tokenizer_mode}")

    try:
        llm = LLM(
            model=model_id,
            tensor_parallel_size=args.tp,
            gpu_memory_utilization=args.gpu_mem_util,
            enforce_eager=True,
            swap_space=0,
            dtype="bfloat16",
            # tokenizer_mode=tokenizer_mode,  # if your vLLM version supports it
        )
    except Exception as e:
        sys.exit(f"❌ Failed to initialize LLM: {e}")

    # Tighter max_tokens since outputs are small JSONs
    sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=256,
        stop=["<|eot_id|>", "<|end_of_text|>", "<|im_end|>"],
    )

    # Load full input table
    df = pd.read_excel(INPUT_FILE)
    all_indices = list(df.index)

    # Resume logic
    processed_indices = get_processed_indices_for_model(model_id)
    remaining_indices = [i for i in all_indices if i not in processed_indices]
    total_remaining = len(remaining_indices)

    if total_remaining == 0:
        print(f"✅ Nothing to do: all {len(all_indices)} rows are already processed for model '{model_id}'.")
        return

    if args.limit is None or args.limit == 0:
        print("⚠️ limit=0 -> nothing to run.")
        return
    if args.limit > 0:
        remaining_indices = remaining_indices[:args.limit]

    print(f"🧮 Total rows in input: {len(all_indices)}")
    print(f"🧾 Already processed for this model (split_verify): {len(processed_indices)}")
    print(f"📌 Remaining rows BEFORE limit: {total_remaining}")
    print(f"▶️ This run will process: {len(remaining_indices)} rows")

    if not remaining_indices:
        print("✅ No new rows to process after applying limit.")
        return

    results = []

    # ====== BATCHED 3-STAGE PIPELINE ======
    for batch_indices in chunked(remaining_indices, BATCH_SIZE):
        # Collect valid questions for this batch
        questions = []
        for idx in batch_indices:
            row = df.loc[idx]
            q = row.get("Query", row.get("question", ""))
            q = "" if pd.isna(q) else str(q).strip()
            if not q:
                print(f"Skipping row {idx}: empty question/query.")
                continue
            questions.append((idx, q))

        if not questions:
            continue

        # ---------- STAGE 1 (batch) ----------
        prompts1 = [build_stage1_prompt(q) for _, q in questions]
        t0 = time.time()
        out1 = llm.generate(prompts1, sampling_params)
        t_stage1 = time.time() - t0

        filters_stage1 = []
        for (idx, q), out in zip(questions, out1):
            raw = out.outputs[0].text
            o1 = parse_json_safe(raw) or {}
            sel_f_raw = o1.get("selected_filter", {})
            filters_stage1.append(normalize_selected_filter(sel_f_raw))

        # ---------- STAGE 2 (batch) ----------
        prompts2 = [
            build_stage2_prompt(q, f_sel)
            for (idx, q), f_sel in zip(questions, filters_stage1)
        ]
        t0 = time.time()
        out2 = llm.generate(prompts2, sampling_params)
        t_stage2 = time.time() - t0

        columns_stage2 = []
        for (idx, q), out in zip(questions, out2):
            raw = out.outputs[0].text
            o2 = parse_json_safe(raw) or {}
            cols_obj = normalize_selected_column(o2.get("selected_column", {}))
            columns_stage2.append(cols_obj)

        # ---------- STAGE 3 (batch) ----------
        prompts3 = [
            build_stage3_prompt(q, f_sel, c_sel)
            for (idx, q), f_sel, c_sel in zip(questions, filters_stage1, columns_stage2)
        ]
        t0 = time.time()
        out3 = llm.generate(prompts3, sampling_params)
        t_stage3 = time.time() - t0

        # ---------- MERGE + APPROX PER-ROW TIMINGS ----------
        n_batch = len(questions)
        per_row_stage1 = t_stage1 / n_batch
        per_row_stage2 = t_stage2 / n_batch
        per_row_stage3 = t_stage3 / n_batch
        per_row_total  = (t_stage1 + t_stage2 + t_stage3) / n_batch

        for (idx, q), f_sel, c_sel, out in zip(questions, filters_stage1, columns_stage2, out3):
            raw3 = out.outputs[0].text
            o3 = parse_json_safe(raw3) or {}
            status = str(o3.get("status", "")).strip().lower()

            if status == "revise":
                sel_f = o3.get("selected_filter", f_sel)
                sel_c = o3.get("selected_column", c_sel)
                f_final = normalize_selected_filter(sel_f)
                c_final = normalize_selected_column(sel_c)
            elif status == "accept":
                f_final = normalize_selected_filter(o3.get("selected_filter", f_sel))
                c_final = normalize_selected_column(o3.get("selected_column", c_sel))
            else:
                f_final = normalize_selected_filter(f_sel)
                c_final = normalize_selected_column(c_sel)

            results.append({
                "Original_Index": idx,
                "Query": q,
                "Parsed_Filter": json.dumps(f_final, ensure_ascii=False),
                "Parsed_Column": json.dumps(c_final, ensure_ascii=False),
                "stage1_time_sec": per_row_stage1,
                "stage2_time_sec": per_row_stage2,
                "stage3_time_sec": per_row_stage3,
                "total_time_sec": per_row_total,
            })

    if not results:
        print("⚠️ No rows were actually processed.")
        return

    output_df = pd.DataFrame(results)

    os.makedirs(EXPERIMENT_RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    clean_model_name = model_id.split("/")[-1]
    run_type = f"limit-{len(remaining_indices)}"

    output_filename = os.path.join(
        EXPERIMENT_RESULTS_DIR,
        f"{clean_model_name}_{run_type}_{timestamp}.xlsx"
    )

    output_df.to_excel(output_filename, index=False)
    print(f"\n✅ split_verify (batched) results saved: {output_filename}")

    try:
        from vllm.distributed.parallel_state import destroy_model_parallel
        destroy_model_parallel()
    except Exception:
        pass

    del llm
    gc.collect()
    torch.cuda.empty_cache()

if __name__ == "__main__":
    main()
