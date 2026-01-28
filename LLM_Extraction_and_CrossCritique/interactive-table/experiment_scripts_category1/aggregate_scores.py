#!/usr/bin/env python

"""
aggregate_evals_formatted.py

Aggregate evaluation metrics from all pipelines and save them in a
single Excel sheet with the layout:

500 Question of Category 1
        <Model A>                 <Model B>                 <Model C> ...
        Filter Selection  Column Selection  Filter Selection  Column Selection  ...
Pipeline  Avg Precision  Avg Recall  Avg Precision  Avg Recall  ... (for each model)
Direct Prompting - Baseline
Split Function Approach
Separate Selection + Verifier
Rank And Revise - Self Consistency

Key changes:
- Dynamically includes *all* models found in results (no fixed MODEL_ORDER).
- If filenames use HF snapshot hashes, resolves them to original model names by searching:
    /mnt/shared/shared_hf_home/hub  (configurable via --hf-cache-dir)
- If aggregated rowcount looks like the “~600-ish” duplicate-question symptom,
  attempts to drop duplicate questions before averaging metrics.

Assumptions:
- Eval files: results/<pipeline>/<model_or_snapshot>_EVAL_<timestamp>.xlsx
- Each eval file includes metric columns:
    precision_filters, recall_filters, precision_columns, recall_columns
"""

import os
import argparse
from collections import defaultdict
from glob import glob

import pandas as pd


# ==========================
# CONFIG / CONSTANTS
# ==========================

DEFAULT_BASE_DIR = "/mnt/data1/srchowd3/Mayo-CoRAL/LLM_Extraction_and_CrossCritique/interactive-table"
RESULTS_SUBDIR = "results"
DEFAULT_HF_CACHE_DIR = "/mnt/shared/shared_hf_home/hub"

PIPELINES = [
    ("base_prompt",      "Direct Prompting - Baseline"),
    ("split_function",   "Split Function Approach"),
    ("split_verify",     "Separate Selection + Verifier"),
    ("self_consistency", "Rank And Revise - Self Consistency"),
]

METRIC_COLS = [
    "precision_filters",
    "recall_filters",
    "precision_columns",
    "recall_columns",
]

# Only apply dedupe when we see the “~600 rows” symptom
DEDUPE_TRIGGER_MIN_ROWS = 550

# Candidate ID columns to dedupe on (best-effort)
DEDUP_ID_CANDIDATES = [
    "question_id",
    "qid",
    "id",
    "example_id",
    "sample_id",
    "idx",
    "index",
    "question_idx",
    "question_num",
    "prompt_id",
    "row_id",
    "uuid",
]

# Optional “pretty” labels for known models (fallback is auto-prettified name)
PREFERRED_MODEL_LABELS = {
    "Meta-Llama-3.1-8B-Instruct": "Llama 3.1 8b",
    "Mistral-7B-Instruct-v0.2": "Mistral 7b",
    "Qwen2.5-7B-Instruct": "Qwen 2.5 7b",
}


# ==========================
# ARG PARSING
# ==========================

def parse_args():
    parser = argparse.ArgumentParser(description="Aggregate eval metrics into a formatted Excel table.")
    parser.add_argument(
        "--base-dir",
        type=str,
        default=DEFAULT_BASE_DIR,
        help=f"Base directory of the project (default: {DEFAULT_BASE_DIR})",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="500 Question of Category 1",
        help="Title to put in the top-left cell.",
    )
    parser.add_argument(
        "--output-name",
        type=str,
        default="eval_summary_formatted.xlsx",
        help="Output Excel filename.",
    )
    parser.add_argument(
        "--hf-cache-dir",
        type=str,
        default=DEFAULT_HF_CACHE_DIR,
        help=f"HuggingFace cache root to resolve snapshot hashes (default: {DEFAULT_HF_CACHE_DIR}).",
    )
    return parser.parse_args()


# ==========================
# HELPERS
# ==========================

def discover_eval_files(pipeline_dir: str) -> dict:
    """
    Return: { model_token: [filepaths...] } for *_EVAL_*.xlsx files.
    model_token is whatever appears left of "_EVAL_" in the filename.
    """
    files_by_model = defaultdict(list)

    if not os.path.isdir(pipeline_dir):
        return files_by_model

    for fname in os.listdir(pipeline_dir):
        if not fname.endswith(".xlsx"):
            continue
        if "_EVAL_" not in fname:
            continue

        stem = os.path.splitext(fname)[0]
        left, _sep, _right = stem.partition("_EVAL_")
        if not left:
            continue

        files_by_model[left].append(os.path.join(pipeline_dir, fname))

    return files_by_model


def _looks_like_snapshot_hash(s: str) -> bool:
    # snapshot hashes are typically 40 hex chars
    if len(s) != 40:
        return False
    return all(c in "0123456789abcdef" for c in s.lower())


def resolve_model_token(model_token: str, hf_cache_dir: str) -> str:
    """
    If model_token is an HF snapshot hash, resolve to the repo name by searching the HF cache.
    Otherwise return model_token unchanged.
    """
    if not _looks_like_snapshot_hash(model_token):
        return model_token

    # Typical layout: <hf_cache_dir>/models--org--repo/snapshots/<hash>
    pattern = os.path.join(hf_cache_dir, "models--*", "snapshots", model_token)
    matches = glob(pattern)

    if not matches:
        # Fallback recursive
        pattern2 = os.path.join(hf_cache_dir, "**", "snapshots", model_token)
        matches = glob(pattern2, recursive=True)

    if not matches:
        return model_token

    snap_path = matches[0]
    models_dir = os.path.basename(os.path.dirname(os.path.dirname(snap_path)))
    # models_dir example: "models--meta-llama--Meta-Llama-3.1-8B-Instruct"
    if not models_dir.startswith("models--"):
        return model_token

    parts = models_dir.split("--")
    if len(parts) >= 3:
        repo = "--".join(parts[2:])
        return repo

    return model_token


def prettify_model_name(name: str) -> str:
    """
    Produce a readable header label if not in PREFERRED_MODEL_LABELS.
    """
    if name in PREFERRED_MODEL_LABELS:
        return PREFERRED_MODEL_LABELS[name]

    # basic prettify: replace dashes with spaces, collapse double spaces
    pretty = name.replace("_", " ").replace("-", " ").strip()
    while "  " in pretty:
        pretty = pretty.replace("  ", " ")
    return pretty


def _choose_dedup_key_cols(df: pd.DataFrame) -> tuple[list[str], str]:
    cols = list(df.columns)

    for c in DEDUP_ID_CANDIDATES:
        if c in cols:
            return [c], f"using id column '{c}'"

    non_metric = [c for c in cols if c not in METRIC_COLS]
    if non_metric:
        return non_metric, "using all non-metric columns"

    return [], "no suitable key columns found"


def aggregate_for_model(files) -> tuple[int, int, dict]:
    """
    Returns (n_rows_raw, n_rows_used, metrics_dict)
    """
    frames = []
    for fpath in files:
        try:
            df = pd.read_excel(fpath)
        except Exception as e:
            print(f"⚠️ Could not read eval file {fpath}: {e}")
            continue

        existing_metrics = [m for m in METRIC_COLS if m in df.columns]
        if not existing_metrics:
            print(f"⚠️ No metric columns found in {fpath}; skipping.")
            continue

        # Keep full DF (so we can dedupe using IDs if present)
        frames.append(df)

    if not frames:
        return 0, 0, {}

    all_df = pd.concat(frames, ignore_index=True)
    n_rows_raw = len(all_df)

    # Only dedupe for the “~600-ish” case
    if n_rows_raw >= DEDUPE_TRIGGER_MIN_ROWS:
        key_cols, reason = _choose_dedup_key_cols(all_df)
        if key_cols:
            before = len(all_df)
            all_df = all_df.drop_duplicates(subset=key_cols, keep="first").reset_index(drop=True)
            after = len(all_df)
            removed = before - after
            if removed > 0:
                print(f"    🧹 De-duped {removed} duplicate rows ({reason}). New rows={after}.")
        else:
            print("    ⚠️ Wanted to dedupe (rowcount high) but couldn't find usable key columns; leaving as-is.")

    n_rows_used = len(all_df)

    metrics = {}
    for m in METRIC_COLS:
        if m in all_df.columns:
            metrics[m] = float(all_df[m].mean())

    return n_rows_raw, n_rows_used, metrics


def order_models(models: list[str]) -> list[str]:
    """
    Keep preferred/known models first (in a stable order), then append the rest sorted.
    """
    preferred_order = [m for m in PREFERRED_MODEL_LABELS.keys() if m in models]
    remaining = sorted([m for m in models if m not in set(preferred_order)])
    return preferred_order + remaining


# ==========================
# MAIN
# ==========================

def main():
    args = parse_args()

    base_dir = args.base_dir
    results_dir = os.path.join(base_dir, RESULTS_SUBDIR)
    os.makedirs(results_dir, exist_ok=True)

    print("===========================================")
    print(f"Base dir    : {base_dir}")
    print(f"Results dir : {results_dir}")
    print(f"HF cache dir: {args.hf_cache_dir}")
    print("===========================================")

    # metrics_by[(pipeline_name, model_name)] = metrics dict
    metrics_by = {}
    rows_by = {}   # (pipeline, model) -> (raw_rows, used_rows)
    all_models_found = set()

    for pipeline_name, _pipeline_label in PIPELINES:
        pipeline_dir = os.path.join(results_dir, pipeline_name)
        print(f"\n🔎 Scanning pipeline: {pipeline_name} ({pipeline_dir})")

        files_by_token = discover_eval_files(pipeline_dir)
        if not files_by_token:
            print("  ⚠️ No *_EVAL_*.xlsx files found.")
            continue

        for model_token, files in files_by_token.items():
            model_name = resolve_model_token(model_token, args.hf_cache_dir)
            all_models_found.add(model_name)

            n_raw, n_used, metrics = aggregate_for_model(files)
            if n_used == 0 or not metrics:
                print(f"  ⚠️ No usable rows/metrics for model {model_name}; skipping.")
                continue

            metrics_by[(pipeline_name, model_name)] = metrics
            rows_by[(pipeline_name, model_name)] = (n_raw, n_used)

            print(
                f"  ▶ {pipeline_name} / {model_name}: "
                f"rows(raw→used)={n_raw}→{n_used}, "
                f"F_P={metrics.get('precision_filters', float('nan')):.3f}, "
                f"F_R={metrics.get('recall_filters', float('nan')):.3f}, "
                f"C_P={metrics.get('precision_columns', float('nan')):.3f}, "
                f"C_R={metrics.get('recall_columns', float('nan')):.3f}"
            )

    if not all_models_found:
        print("\n⚠️ No models found. Exiting.")
        return

    model_list = order_models(list(all_models_found))

    out_xlsx = os.path.join(results_dir, args.output_name)
    print(f"\n📝 Writing formatted summary to: {out_xlsx}")

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        wb = writer.book

        # Remove default sheet if it exists and is empty-ish
        if wb.sheetnames and wb.sheetnames[0] != "Summary" and len(wb.sheetnames) == 1:
            wb.remove(wb[wb.sheetnames[0]])

        ws = wb.create_sheet("Summary") if "Summary" not in wb.sheetnames else wb["Summary"]

        # Row 1: title
        ws.cell(row=1, column=1, value=args.title)

        # Row 2: model names (each model gets 4 columns)
        # Col 1 = Pipeline, then model groups start at col 2, 6, 10, ...
        for mi, model_name in enumerate(model_list):
            start_col = 2 + mi * 4
            ws.cell(row=2, column=start_col, value=prettify_model_name(model_name))

        # Row 3: Filter Selection / Column Selection labels per model
        for mi in range(len(model_list)):
            start_col = 2 + mi * 4
            ws.cell(row=3, column=start_col,     value="Filter Selection")
            ws.cell(row=3, column=start_col + 2, value="Column Selection")

        # Row 4: metric headers
        ws.cell(row=4, column=1, value="Pipeline")
        for mi in range(len(model_list)):
            start_col = 2 + mi * 4
            ws.cell(row=4, column=start_col,     value="Avg Precision")  # Filter P
            ws.cell(row=4, column=start_col + 1, value="Avg Recall")     # Filter R
            ws.cell(row=4, column=start_col + 2, value="Avg Precision")  # Column P
            ws.cell(row=4, column=start_col + 3, value="Avg Recall")     # Column R

        # Data rows (one per pipeline)
        start_row = 5
        for pi, (pipeline_name, pipeline_label) in enumerate(PIPELINES):
            row = start_row + pi
            ws.cell(row=row, column=1, value=pipeline_label)

            for mi, model_name in enumerate(model_list):
                start_col = 2 + mi * 4
                metrics = metrics_by.get((pipeline_name, model_name))
                if not metrics:
                    continue

                ws.cell(row=row, column=start_col,     value=metrics.get("precision_filters"))
                ws.cell(row=row, column=start_col + 1, value=metrics.get("recall_filters"))
                ws.cell(row=row, column=start_col + 2, value=metrics.get("precision_columns"))
                ws.cell(row=row, column=start_col + 3, value=metrics.get("recall_columns"))

    print("✅ Done.")


if __name__ == "__main__":
    main()
