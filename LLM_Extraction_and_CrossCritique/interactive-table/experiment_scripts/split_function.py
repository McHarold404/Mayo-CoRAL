import pandas as pd
import json
import re
import os
import argparse
import sys
import torch
import gc
from datetime import datetime
from dotenv import load_dotenv
from vllm import LLM, SamplingParams

# ============================
# CONFIGURATION
# ============================

load_dotenv()

BASE_DIR = "/scratch/srchowd3/Mayo-CoRAL/LLM_Extraction_and_CrossCritique/interactive-table"
INPUT_FILE = f"{BASE_DIR}/runs/query-chosen-filters-columns - full.xlsx"
RESULTS_DIR = f"{BASE_DIR}/results"

# one subfolder for this script inside results/
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
EXPERIMENT_RESULTS_DIR = os.path.join(RESULTS_DIR, SCRIPT_NAME)

DEF_FOLDER = f"{BASE_DIR}/definitions_folder"
FILTER_NAMES_PATH = f"{DEF_FOLDER}/definitions - aim2 - filter names.txt"
COLUMN_DEFS_PATH  = f"{DEF_FOLDER}/definitions - aim2 - column.txt"
FILTER_DEFS_FULL_PATH = f"{DEF_FOLDER}/definitions - aim2 - filter.txt"

# ---------- GROUND TRUTH COLUMN NAMES ----------
# Both filter + column GT live in the same JSON column (like in your base script)
GT_FILTER_COL = "Ground Truth JSON"
GT_COLUMN_COL = "Ground Truth JSON"
# ------------------------------------------------

# Get HF_TOKEN (Required)
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    sys.exit("❌ Error: HF_TOKEN not found in .env file or environment variables.")

# DEFAULT MODEL (you’ll override with --model)
DEFAULT_MODEL_ID = os.getenv("MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.2")

# Columns that are always included by default
REQUIRED_COLS = ["NCT", "PMID", "Authors", "Year"]
MAX_ADDITIONAL_COLS = 6

# ============================
# ENVIRONMENT (SAFE)
# ============================
os.environ["HF_TOKEN"] = HF_TOKEN
if not os.environ.get("HF_HOME"):
    os.environ["HF_HOME"] = "/scratch/srchowd3/models"

# ============================
# SETUP & LOADING
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
# HELPERS FOR JSON
# ============================

def strip_code_fences(s: str) -> str:
    s = str(s).strip()
    if s.startswith("```"):
        s = s[s.find("\n") + 1:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()

def parse_json_safe(text):
    # Parse JSON robustly from a string or object. Returns None on failure.
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    if isinstance(text, (dict, list)):
        return text

    raw = strip_code_fences(text)

    # Direct parse
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Try first {...} block
    try:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end+1])
    except Exception:
        pass

    return None

def extract_json(text: str):
    return parse_json_safe(text)

# ============================
# PROMPT BUILDERS (PIPELINE 2)
# ============================

def build_stage1_prompt(question: str) -> str:
    total_slots = len(REQUIRED_COLS) + MAX_ADDITIONAL_COLS
    schema_columns = ',\n'.join([f'    "Column {i}": "Name"' for i in range(1, total_slots + 1)])

    schema = (
        '{\n'
        '  "selected_filter_names": ["Filter Category 1", "Filter Category 2"],\n'
        '  "selected_column": {\n'
        f'{schema_columns}\n'
        '  }\n'
        '}'
    )

    example_obj = {
        "selected_filter_names": ["Cancer type", "Trial phase", "Class of ICI"],
        "selected_column": {
            "Column 1": "NCT",
            "Column 2": "PMID",
            "Column 3": "Authors",
            "Column 4": "Year",
            "Column 5": "Primary Endpoint(s)",
            "Column 6": "Sample Size"
        }
    }
    example = json.dumps(example_obj, ensure_ascii=False)

    return (
        "You are a medical expert researching cancer.\n"
        "Stage 1: choose relevant FILTER CATEGORY NAMES (names only, do not assign values yet) "
        "and choose up to additional columns beyond NCT, PMID, Authors, and Year.\n\n"
        "Return ONLY a valid JSON object (no prose, no code fences) with this schema:\n"
        f"{schema}\n\n"
        "Rules:\n"
        f"- NCT, PMID, Authors, and Year are ALWAYS included by default unless explicitly excluded.\n"
        f"- You may add at most {MAX_ADDITIONAL_COLS} additional columns beyond those four default columns.\n"
        "- Include only columns justified by the question.\n"
        "- Also select the relevant FILTER CATEGORY NAMES (do NOT assign values yet).\n"
        "- Use exact names from the lists provided.\n"
        "- Use double quotes. No trailing commas. No explanations.\n\n"
        "Available filter CATEGORY NAMES (choose names only; do NOT assign values):\n"
        f"{FILTER_NAMES_TEXT}\n\n"
        "Available columns and definitions (select by exact name):\n"
        f"{COLUMN_DEFS_TEXT}\n\n"
        f"Question: {question}\n"
        "Return JSON now.\n"
        f"Example of valid formatting (not prescriptive): {example}"
    )

def build_stage2_prompt(question: str, selected_filter_names, selected_column_obj) -> str:
    schema = (
        '{\n'
        '  "selected_filter": {\n'
        '    "Filter Category 1": "Chosen Value",\n'
        '    "Filter Category 2": "Chosen Value"\n'
        '  }\n'
        '}'
    )
    chosen_cols_json = json.dumps(selected_column_obj, ensure_ascii=False)
    chosen_names_json = json.dumps(selected_filter_names, ensure_ascii=False)
    example = '{"selected_filter":{"Cancer type":"NSCLC","Trial phase":"Phase III"}}'

    return (
        "You are a medical expert researching cancer.\n"
        "Stage 2: based on the chosen filter CATEGORY NAMES, pick specific values using the full filter definitions.\n"
        "Keep the chosen columns as context when deciding on filter values.\n\n"
        "Return ONLY a valid JSON object (no prose, no code fences) with this schema:\n"
        f"{schema}\n\n"
        "Rules:\n"
        "- Use double quotes.\n"
        "- Choose filter values ONLY for the provided category names.\n"
        "- Omit any filters whose correct value would be 'All'.\n"
        "- Include only filters that are justified by the question.\n"
        "- Use exact category and value strings from the definitions.\n"
        "- Do not include any explanation.\n\n"
        f"Chosen filter CATEGORY NAMES (names only; restrict your value choices to these):\n{chosen_names_json}\n\n"
        "Chosen columns (REQUIRED + additional):\n"
        f"{chosen_cols_json}\n\n"
        "Available filter CATEGORY NAMES (for reference):\n"
        f"{FILTER_NAMES_TEXT}\n\n"
        "Available FULL filter categories and values (use exact category and value strings):\n"
        f"{FILTER_DEFS_TEXT}\n\n"
        "Available columns and definitions (for context when choosing filters):\n"
        f"{COLUMN_DEFS_TEXT}\n\n"
        f"Question: {question}\n"
        "Return JSON now.\n"
        f"Example of valid formatting (not prescriptive): {example}"
    )

# ============================
# NORMALIZATION & CONVERSION
# ============================

def _ordered_values_from_column_object(col_obj: dict) -> list:
    if not isinstance(col_obj, dict):
        return []
    items = []
    for k, v in col_obj.items():
        m = re.search(r"Column\s*(\d+)", str(k))
        idx = int(m.group(1)) if m else 10**9
        items.append((idx, v))
    items.sort(key=lambda x: x[0])
    return [val for _, val in items if isinstance(val, str) and val.strip()]

def normalize_selected_column_object(selected_column) -> dict:
    if isinstance(selected_column, dict):
        cols = _ordered_values_from_column_object(selected_column)
    elif isinstance(selected_column, list):
        cols = [c for c in selected_column if isinstance(c, str) and c.strip()]
    else:
        cols = []

    out_list = []
    seen = set()
    for rc in REQUIRED_COLS:
        if rc not in seen:
            out_list.append(rc)
            seen.add(rc)
    for c in cols:
        if c not in seen:
            seen.add(c)
            out_list.append(c)

    cap = len(REQUIRED_COLS) + MAX_ADDITIONAL_COLS
    out_list = out_list[:cap]

    return {f"Column {i+1}": name for i, name in enumerate(out_list)}

def normalize_filter_names(names):
    names = [n for n in (names or []) if isinstance(n, str) and n.strip()]
    seen = set()
    unique = []
    for n in names:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    return unique[:10]

def normalize_selected_filter(selected_filter: dict) -> dict:
    out = {}
    for k, v in (selected_filter or {}).items():
        if v is None:
            continue
        s = str(v).strip()
        if not s or s.lower() == "all":
            continue
        out[str(k).strip()] = s
    return out

# Canonical names for FILTER CATEGORIES (keys)
FILTER_NAME_CANON = {
    "Class of ICI": "Class of ICI",
    "Cancer type": "Cancer type",
    "Monotherapy/combination": "Monotherapy/combination",
    "Trial phase": "Trial phase",
    "Clinical setting in relation to surgery": "Clinical setting in relation to surgery",
    "Primary endpoint": "Primary endpoint",
    "Total sample size": "Total sample size",
    "Year": "Year",

    "ICI Class": "Class of ICI",
    "ICI class": "Class of ICI",
    "Checkpoint class": "Class of ICI",

    "Cancer Type": "Cancer type",
    "Disease": "Cancer type",
    "Indication": "Cancer type",
    "Cancer type – The specific disease/indication under study (e.g., metastatic castration-sensitive prostate cancer, NSCLC, melanoma), including stage/setting when relevant.": "Cancer type",

    "Type of Therapy": "Monotherapy/combination",
    "Monotherapy/Combination": "Monotherapy/combination",
    "Monotherapy vs Combination": "Monotherapy/combination",
    "Mono/Combo": "Monotherapy/combination",

    "Trial Phase": "Trial phase",
    "Clinical Trial Phase": "Trial phase",
    "Phase": "Trial phase",

    "Clinical setting": "Clinical setting in relation to surgery",
    "Perioperative setting": "Clinical setting in relation to surgery",
    "Setting in relation to surgery": "Clinical setting in relation to surgery",
}

def canonicalize_names(names):
    out = []
    for n in names:
        key = n.strip()
        canon = FILTER_NAME_CANON.get(key, key)
        if canon not in out:
            out.append(canon)
    return out

# ============================
# RESUME LOGIC
# ============================

def get_processed_indices_for_model(model_id: str):
    """
    Find which Original_Index rows have already been processed for this model,
    based on files in results/<SCRIPT_NAME>/ starting with <model-safename>_*.xlsx.
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
                    processed.update(df_res["Original_Index"].dropna().astype(int).tolist())
            except Exception as e:
                print(f"⚠️ Could not read results file {fname}: {e}")

    print(f"📂 Found {len(processed)} processed rows for model '{model_id}'.")
    return processed

# ============================
# EVAL HELPERS (PRECISION/RECALL)
# ============================

def load_all_results_for_model(model_id: str) -> pd.DataFrame | None:
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
        df_all = df_all.sort_index().drop_duplicates(subset=["Original_Index"], keep="last")

    return df_all

def precision_recall(pred_set, true_set):
    pred = set(pred_set)
    true = set(true_set)

    if not pred and not true:
        return 1.0, 1.0

    tp = len(pred & true)
    precision = tp / len(pred) if pred else 0.0
    recall    = tp / len(true) if true else 0.0
    return precision, recall

def evaluate_model_precision_recall(model_id: str):
    print(f"\n🔍 Starting evaluation for model: {model_id}")
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

        pred_filter = parse_json_safe(row.get("Parsed_Filter", "{}"))
        pred_cols   = parse_json_safe(row.get("Parsed_Column", "{}"))

        gt_obj = parse_json_safe(gt_row.get(GT_FILTER_COL, "{}"))

        if isinstance(gt_obj, dict):
            gt_filter_raw = gt_obj.get("selected_filter", {})
            gt_cols_raw   = gt_obj.get("selected_column", {})
        else:
            gt_filter_raw = {}
            gt_cols_raw   = {}

        pred_filter_norm = normalize_selected_filter(pred_filter or {})
        gt_filter_norm   = normalize_selected_filter(gt_filter_raw or {})

        pred_cols_norm = normalize_selected_column_object(pred_cols or {})
        gt_cols_norm   = normalize_selected_column_object(gt_cols_raw or {})

        pred_filter_items = set(pred_filter_norm.items())
        gt_filter_items   = set(gt_filter_norm.items())

        pred_col_names = set(pred_cols_norm.values())
        gt_col_names   = set(gt_cols_norm.values())

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
# TWO-STAGE GENERATION
# ============================

def run_two_stage_for_indices(df, indices, model_id, llm, sampling_params):
    stage1_prompts = []
    meta = []  # (idx, question)
    for idx in indices:
        row = df.loc[idx]
        question = row.get("Query", row.get("question", ""))
        if not isinstance(question, str):
            question = str(question)
        stage1_prompts.append(build_stage1_prompt(question))
        meta.append((idx, question))

    print(f"Running stage 1 for {len(stage1_prompts)} items...")
    stage1_outputs = llm.generate(stage1_prompts, sampling_params)

    selected_filter_names_list = []
    selected_column_objs = []

    for (idx, question), out in zip(meta, stage1_outputs):
        text = out.outputs[0].text
        obj = extract_json(text) or {}
        raw_names = obj.get("selected_filter_names", [])
        raw_cols  = obj.get("selected_column", {})
        names_norm = normalize_filter_names(raw_names)
        names_norm = canonicalize_names(names_norm)
        cols_norm  = normalize_selected_column_object(raw_cols)
        selected_filter_names_list.append(names_norm)
        selected_column_objs.append(cols_norm)

    stage2_prompts = []
    for (idx, question), names_norm, cols_norm in zip(meta, selected_filter_names_list, selected_column_objs):
        stage2_prompts.append(build_stage2_prompt(question, names_norm, cols_norm))

    print(f"Running stage 2 for {len(stage2_prompts)} items...")
    stage2_outputs = llm.generate(stage2_prompts, sampling_params)

    results = []
    for i, ((idx, question), cols_norm, out2) in enumerate(zip(meta, selected_column_objs, stage2_outputs)):
        text1 = stage1_outputs[i].outputs[0].text
        text2 = out2.outputs[0].text
        obj2 = extract_json(text2) or {}
        sel_filter_raw = obj2.get("selected_filter", {})
        sel_filter_norm = normalize_selected_filter(sel_filter_raw)

        sel_filter_str = json.dumps(sel_filter_norm)
        sel_column_str = json.dumps(cols_norm)

        results.append({
            "Original_Index": idx,
            "Query": question,
            "Generated_Raw_Stage1": text1,
            "Generated_Raw_Stage2": text2,
            "Parsed_Filter": sel_filter_str,
            "Parsed_Column": sel_column_str,
        })

    return results

# ============================
# MAIN
# ============================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["run", "eval"],
        default="run",
        help="'run' = generate with LLM (two-stage pipeline), 'eval' = compute precision/recall only."
    )
    parser.add_argument("--limit", type=int, default=1,
                        help="Maximum number of NEW (unprocessed) rows to run. -1 = all remaining.")
    parser.add_argument("--start", type=int, default=0,
                        help="(Unused with resume, kept for compatibility).")
    parser.add_argument("--tp", type=int, default=torch.cuda.device_count())
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL_ID)
    args = parser.parse_args()

    model_id = args.model.strip().rstrip(",")

    # ---------- EVAL-ONLY MODE ----------
    if args.mode == "eval":
        evaluate_model_precision_recall(model_id)
        return
    # -----------------------------------

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
            gpu_memory_utilization=0.50,
            enforce_eager=True,
            swap_space=0,
            dtype="bfloat16",
        )
    except Exception as e:
        sys.exit(f"❌ Failed to initialize LLM: {e}")

    sampling_params = SamplingParams(
        temperature=0.1,
        max_tokens=1000,
        stop=["<|eot_id|>", "<|end_of_text|>", "<|im_end|>"],
    )

    df = pd.read_excel(INPUT_FILE)
    all_indices = list(df.index)

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
    print(f"🧾 Already processed for this model: {len(processed_indices)}")
    print(f"📌 Remaining rows BEFORE limit: {total_remaining}")
    print(f"▶️ This run will process: {len(remaining_indices)} rows")

    if not remaining_indices:
        print("✅ No new rows to process after applying limit.")
        return

    results = run_two_stage_for_indices(df, remaining_indices, model_id, llm, sampling_params)

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
    print(f"\n✅ Results saved: {output_filename}")

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
