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

# ---------- GROUND TRUTH COLUMN NAMES ----------
# These must exist in INPUT_FILE and contain JSON ground truth.
# Adjust these to match your spreadsheet.
GT_FILTER_COL = "Ground Truth JSON"
GT_COLUMN_COL = "Ground Truth JSON"
# ------------------------------------------------

# Get HF_TOKEN (Required)
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    sys.exit("❌ Error: HF_TOKEN not found in .env file or environment variables.")

# DEFAULT MODEL
DEFAULT_MODEL_ID = os.getenv("MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.2")

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
# PROMPT CONSTRUCTION
# ============================

def get_system_prompt():
    schema = (
        '{\n'
        '  "selected_filter": {\n'
        '    "Filter Category 1": "Chosen Value",\n'
        '    "Filter Category 2": "Chosen Value"\n'
        '  },\n'
        '  "selected_column": {\n'
        '    "Column 1": "Name",\n'
        '    "Column 2": "Name",\n'
        '    "Column 3": "Name",\n'
        '    "Column 4": "Name",\n'
        '    "Column 5": "Name",\n'
        '    "Column 6": "Name",\n'
        '    "Column 7": "Name",\n'
        '    "Column 8": "Name",\n'
        '    "Column 9": "Name",\n'
        '    "Column 10": "Name"\n'
        '  }\n'
        '}'
    )

    example = (
        '{'
        '"selected_filter":{"Cancer Type":"NSCLC","Trial Phase":"Phase 3","Type of Therapy":"Combination Therapy"},'
        '"selected_column":{"Column 1":"NCT","Column 2":"PMID","Column 3":"Authors","Column 4":"Year","Column 5":"Primary Endpoint","Column 6":"Sample Size","Column 7":"Name of ICI","Column 8":"Control regimen","Column 9":"Monotherapy/combination","Column 10":"Lines of treatment"}'
        '}'
    )

    return (
        "You are a medical expert researching cancer trials. Build the ENTIRE selection in ONE step.\n"
        "Return ONLY a valid JSON object (no prose, no code fences) with this schema:\n"
        f"{schema}\n"
        "Strict rules:\n"
        f"- Columns: ALWAYS include these first (do NOT count toward the limit): {', '.join(REQUIRED_COLS)}.\n"
        f"- You may add at most {MAX_ADDITIONAL_COLS} additional columns beyond those required.\n"
        "- The enumerated object keys MUST be exactly 'Column 1', 'Column 2', ... in display order.\n"
        "- Use *exact* names from the available column list.\n"
        "- Filters: choose only categories/values justified by the question. If a category would be 'All', OMIT that category entirely.\n"
        "- Use *exact* category and value strings from the available filter definitions.\n"
        "- Use double quotes everywhere. No trailing commas. No explanations.\n\n"
        "Available filter CATEGORY NAMES:\n"
        f"{FILTER_NAMES_TEXT}\n\n"
        "Available FULL filter categories and values:\n"
        f"{FILTER_DEFS_TEXT}\n\n"
        "Available columns and definitions:\n"
        f"{COLUMN_DEFS_TEXT}\n\n"
        "Return JSON now. Example:\n"
        f"{example}"
    )

def prepare_prompts_for_indices(df, indices, model_id):
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=HF_TOKEN)

    prompts, out_indices = [], []
    subset = df.loc[indices]
    system_content = get_system_prompt()

    for index, row in subset.iterrows():
        query = row.get("Query", row.get("question", ""))
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"Question: {query}"}
        ]
        
        try:
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except Exception as e:
            print(f"⚠️ Warning: apply_chat_template failed ({e}). Using raw formatting.")
            prompt = (
                f"<|im_start|>system\n{system_content}<|im_end|>\n"
                f"<|im_start|>user\n{query}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            )

        prompts.append(prompt)
        out_indices.append(index)

    return prompts, out_indices

# ============================
# NORMALIZATION & JSON UTILS
# ============================

def strip_code_fences(s: str) -> str:
    s = str(s).strip()
    if s.startswith("```"):
        s = s[s.find("\n") + 1:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()

def parse_json_safe(text):
    """Parse JSON robustly from a string or object. Returns None on failure."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    if isinstance(text, dict) or isinstance(text, list):
        # already parsed
        return text

    raw = strip_code_fences(text)

    # Try direct parse
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Try extracting first {...} block
    try:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end+1])
    except Exception:
        pass

    return None

def extract_json(text: str):
    # For generation path (backwards compatible)
    return parse_json_safe(text)

def normalize_selected_filter(selected_filter):
    return {
        str(k).strip(): str(v).strip()
        for k, v in (selected_filter or {}).items()
        if v and str(v).strip().lower() != "all"
    }

def normalize_selected_column_object(selected_column):
    cols = []
    if isinstance(selected_column, dict):
        for k, v in selected_column.items():
            if isinstance(v, str):
                m = re.search(r"Column\s*(\d+)", str(k))
                cols.append((int(m.group(1)) if m else 9999, v))
        cols = [v for _, v in sorted(cols)]
    elif isinstance(selected_column, list):
        cols = [c for c in selected_column if isinstance(c, str)]

    out, seen = [], set()
    for c in REQUIRED_COLS + cols:
        if c not in seen:
            seen.add(c)
            out.append(c)
    out = out[:len(REQUIRED_COLS) + MAX_ADDITIONAL_COLS]
    return {f"Column {i+1}": c for i, c in enumerate(out)}

# ============================
# RESUME LOGIC
# ============================

def get_processed_indices_for_model(model_id: str):
    """
    Collect all Original_Index values that were already processed for this model.
    Looks in the single experiment folder:
      RESULTS_DIR / SCRIPT_NAME
    and filters by filename prefix clean_model_name_.
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
# EVAL HELPERS
# ============================

def load_all_results_for_model(model_id: str) -> pd.DataFrame | None:
    """Load and concatenate all result files for a given model."""
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

    # If you re-ran some rows, keep the *last* occurrence per Original_Index
    if "Original_Index" in df_all.columns:
        df_all = df_all.dropna(subset=["Original_Index"])
        df_all["Original_Index"] = df_all["Original_Index"].astype(int)
        df_all = df_all.sort_index().drop_duplicates(subset=["Original_Index"], keep="last")

    return df_all

def load_all_results_for_model(model_id: str) -> pd.DataFrame | None:
    """Load and concatenate all result files for a given model."""
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

    # If you re-ran some rows, keep the *last* occurrence per Original_Index
    if "Original_Index" in df_all.columns:
        df_all = df_all.dropna(subset=["Original_Index"])
        df_all["Original_Index"] = df_all["Original_Index"].astype(int)
        df_all = (
            df_all
            .sort_index()
            .drop_duplicates(subset=["Original_Index"], keep="last")
        )

    return df_all


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
      - Items = (category, value) pairs.
    Columns:
      - Items = column names (ignoring order).

    Uses Original_Index to align model outputs with INPUT_FILE rows.
    """
    print(f"\n🔍 Starting evaluation for model: {model_id}")

    # Load predictions
    pred_df = load_all_results_for_model(model_id)
    if pred_df is None or pred_df.empty:
        print("❌ No predictions to evaluate.")
        return

    # Load ground truth table
    full_df = pd.read_excel(INPUT_FILE)

    if GT_FILTER_COL not in full_df.columns or GT_COLUMN_COL not in full_df.columns:
        print(
            f"❌ Ground truth columns '{GT_FILTER_COL}' and/or '{GT_COLUMN_COL}' "
            f"not found in {INPUT_FILE}. Please update GT_FILTER_COL / GT_COLUMN_COL."
        )
        return

    records = []
    n = 0

    # accumulators for averages
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

        # predictions (parsed JSON from strings)
        pred_filter = parse_json_safe(row.get("Parsed_Filter", "{}"))
        pred_cols   = parse_json_safe(row.get("Parsed_Column", "{}"))

        # ground truth (same JSON column used for both; contains full object)
        gt_obj = parse_json_safe(gt_row.get(GT_FILTER_COL, "{}"))

        # Expect something like {"selected_filter": {...}, "selected_column": {...}}
        if isinstance(gt_obj, dict):
            gt_filter_raw = gt_obj.get("selected_filter", {})
            gt_cols_raw   = gt_obj.get("selected_column", {})
        else:
            gt_filter_raw = {}
            gt_cols_raw   = {}

        # Normalize both sides
        pred_filter_norm = normalize_selected_filter(pred_filter or {})
        gt_filter_norm   = normalize_selected_filter(gt_filter_raw or {})

        pred_cols_norm = normalize_selected_column_object(pred_cols or {})
        gt_cols_norm   = normalize_selected_column_object(gt_cols_raw or {})

        # --- Build sets for metrics ---

        # Filters: use (category, value) pairs
        pred_filter_items = set(pred_filter_norm.items())
        gt_filter_items   = set(gt_filter_norm.items())

        # Columns: use just the column names (ignore their "Column 1/2/3" positions)
        pred_col_names = set(pred_cols_norm.values())
        gt_col_names   = set(gt_cols_norm.values())

        # Precision / Recall
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

    # Save detailed evaluation to disk
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
    parser.add_argument("--limit", type=int, default=1,
                        help="Maximum number of NEW (unprocessed) rows to run. -1 = all remaining.")
    parser.add_argument("--start", type=int, default=0,
                        help="(Deprecated when resume is used) starting row index.")
    parser.add_argument("--tp", type=int, default=torch.cuda.device_count())
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL_ID)
    args = parser.parse_args()

    # Validate gpu memory utilization
    if not (0.0 < args.gpu_mem_util <= 1.0):
        raise ValueError(f"--gpu-mem-util must be in (0, 1]. Got {args.gpu_mem_util}")

    # Clean & normalize model_id just in case
    model_id = args.model.strip().rstrip(",")

    # ---------- EVAL-ONLY MODE (NO LLM) ----------
    if args.mode == "eval":
        evaluate_model_exact_match(model_id)
        return
    # ---------------------------------------------

    # ====== GENERATION MODE ======
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

    # Tokenizer mode selection (only used if you later pass it to LLM)
    if "mistral" in model_id.lower():
        tokenizer_mode = "mistral"
    else:
        tokenizer_mode = "auto"

    print(f"🚀 Initializing vLLM with model: {model_id}")
    print("⚠️  Config: Memory Util=0.5, Eager Mode=TRUE, No Max Len (Fix for Mistral v0.2)")
    print(f"🔤 tokenizer_mode = {tokenizer_mode}")

    try:
        llm = LLM(
            model=model_id,
            tensor_parallel_size=args.tp,
            gpu_memory_utilization=args.gpu_mem_util,
            enforce_eager=True,
            swap_space=0,
            dtype="bfloat16",
            # tokenizer_mode=tokenizer_mode,  # uncomment if your vLLM version supports it
        )
    except Exception as e:
        sys.exit(f"❌ Failed to initialize LLM: {e}")

    sampling_params = SamplingParams(
        temperature=0.1,
        max_tokens=1000,
        stop=["<|eot_id|>", "<|end_of_text|>", "<|im_end|>"],
    )

    # Load full input table
    df = pd.read_excel(INPUT_FILE)
    all_indices = list(df.index)

    # Figure out which rows are already processed for this model
    processed_indices = get_processed_indices_for_model(model_id)
    remaining_indices = [i for i in all_indices if i not in processed_indices]
    total_remaining = len(remaining_indices)

    if total_remaining == 0:
        print(f"✅ Nothing to do: all {len(all_indices)} rows are already processed for model '{model_id}'.")
        return

    # Respect --limit (number of NEW rows)
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

    # Build prompts only for those remaining indices
    prompts, indices = prepare_prompts_for_indices(df, remaining_indices, model_id)

    print(f"Starting generation for {len(prompts)} items...")
    outputs = llm.generate(prompts, sampling_params)

    results = []
    for idx, output in zip(indices, outputs):
        generated_text = output.outputs[0].text
        parsed_json = extract_json(generated_text)
        
        if parsed_json:
            sel_filter = normalize_selected_filter(
                parsed_json.get("selected_filter", {})
            )
            sel_column = normalize_selected_column_object(
                parsed_json.get("selected_column", {})
            )
            sel_filter_str = json.dumps(sel_filter)
            sel_column_str = json.dumps(sel_column)
        else:
            sel_filter_str, sel_column_str = "{}", "{}"
        
        results.append({
            "Original_Index": idx,
            "Query": df.loc[idx].get("Query", df.loc[idx].get("question", "")),
            "Generated_Raw": generated_text,
            "Parsed_Filter": sel_filter_str,
            "Parsed_Column": sel_column_str,
        })

    output_df = pd.DataFrame(results)

    # --- single subfolder for this script inside results/ ---
    os.makedirs(EXPERIMENT_RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    clean_model_name = model_id.split("/")[-1]
    run_type = f"limit-{len(remaining_indices)}"

    output_filename = os.path.join(
        EXPERIMENT_RESULTS_DIR,
        f"{clean_model_name}_{run_type}_{timestamp}.xlsx"
    )
    # -------------------------------------------------

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
