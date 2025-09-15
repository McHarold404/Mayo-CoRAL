# Strict compare: result must have the same normalized column set as ground truth.
# Also keep row/values comparison (with 'nct'/'pmid' key; fall back to row-set).

import os, re
from pathlib import Path
from datetime import datetime
import pandas as pd

GROUND_DIR = Path("ground_truths") / "cat3_questions_table"
RUN_DIR = None  # set to a specific run dir if needed, else latest cat3_hybrid_*

def latest_run_dir() -> Path:
    c = sorted(Path("results").glob("cat3_hybrid_*"))
    if not c:
        raise FileNotFoundError("No run folder found under results/cat3_hybrid_*")
    return c[-1]

def parse_q_number(filename: str) -> int | None:
    name = Path(filename).name.lower()
    m = re.search(r"\bq(\d+)_cat3_table\.csv$", name)
    if m: return int(m.group(1))
    m2 = re.match(r"(\d{3})_", name)
    if m2: return int(m2.group(1).lstrip("0") or "0")
    return None

def canonical_col(col: str) -> str:
    c = (col or "").strip()
    base = re.sub(r"[^0-9a-zA-Z]+", "", c).lower()
    # light synonym map (extend as needed)
    synonyms = {
        "author": "authors",
        "authors": "authors",
        "pubmedid": "pmid",
        "pubmed_id": "pmid",
        "pmid": "pmid",
        "cancertype": "cancertype",
        "trialphase": "trialphase",
        "endpointrole": "endpointrole",
        "primaryendpoint": "primaryendpoint",
        "secondaryendpoint": "secondaryendpoint",
        "nct": "nct",
    }
    return synonyms.get(base, base)

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={c: canonical_col(c) for c in df.columns})

def normalize_values(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        try:
            out[col] = pd.to_numeric(out[col], errors="ignore")
        except Exception:
            pass
        if pd.api.types.is_object_dtype(out[col]) or pd.api.types.is_string_dtype(out[col]):
            out[col] = out[col].astype(str).map(lambda x: x.strip())
    return out

def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return normalize_values(normalize_columns(df))

def pick_key(df: pd.DataFrame) -> str | None:
    for k in ["nct", "pmid"]:
        if k in df.columns:
            return k
    return None

def match_result_file(run_dir: Path, qn: int) -> Path | None:
    c1 = run_dir / f"q{qn}_cat3_table.csv"
    if c1.exists(): return c1
    c2 = list(run_dir.glob(f"{qn:03}_*.csv"))
    if c2: return sorted(c2)[0]
    c3 = list(run_dir.glob(f"q{qn}_*.csv"))
    if c3: return sorted(c3)[0]
    return None

def rowset_diff(res: pd.DataFrame, gt: pd.DataFrame, cols: list[str]):
    """Fallback diff with no key: compare unordered sets of row-strings on common columns."""
    res_rows = pd.Series(["|".join(str(x) for x in row) for row in res[cols].fillna("").astype(str).values.tolist()])
    gt_rows  = pd.Series(["|".join(str(x) for x in row) for row in gt[cols].fillna("").astype(str).values.tolist()])
    added_set   = sorted(set(res_rows) - set(gt_rows))
    missing_set = sorted(set(gt_rows) - set(res_rows))
    added_rows   = pd.DataFrame({"row": added_set})
    missing_rows = pd.DataFrame({"row": missing_set})
    mismatched_cells = pd.DataFrame(columns=["column", "result", "truth"])
    return added_rows, missing_rows, mismatched_cells

def diff_two_tables(df_res: pd.DataFrame, df_gt: pd.DataFrame):
    """
    Returns: added_rows, missing_rows, mismatched_cells, missing_cols, extra_cols
    - Column-set strictness: result must contain exactly the same normalized columns as ground truth,
      otherwise it's not an exact match (we still compute row/cell diffs on intersection).
    """
    res_cols = [c for c in df_res.columns]
    gt_cols  = [c for c in df_gt.columns]
    res_set, gt_set = set(res_cols), set(gt_cols)

    # Column diffs
    missing_cols = sorted(list(gt_set - res_set))   # expected but not in result
    extra_cols   = sorted(list(res_set - gt_set))   # present in result but not expected

    # For value comparison, use ONLY the ground-truth columns that ARE present in result
    compare_cols = [c for c in gt_cols if c in res_set]
    if not compare_cols:
        # No overlap at all → everything is "different"
        return (df_res.copy(), df_gt.copy(),
                pd.DataFrame(columns=["column","result","truth"]),
                missing_cols, extra_cols)

    key = pick_key(df_res)
    if (key is None) or (key not in df_gt.columns):
        return (*rowset_diff(df_res, df_gt, compare_cols), missing_cols, extra_cols)

    # Keyed compare
    try:
        res_keyed = df_res.drop_duplicates(subset=[key]).set_index(key)
        gt_keyed  = df_gt.drop_duplicates(subset=[key]).set_index(key)
        cols_no_key = [c for c in compare_cols if c != key]

        added_keys   = sorted(set(res_keyed.index) - set(gt_keyed.index))
        missing_keys = sorted(set(gt_keyed.index) - set(res_keyed.index))

        added_rows   = (res_keyed.loc[added_keys, cols_no_key].reset_index()
                        if added_keys else pd.DataFrame(columns=[key] + cols_no_key))
        missing_rows = (gt_keyed.loc[missing_keys, cols_no_key].reset_index()
                        if missing_keys else pd.DataFrame(columns=[key] + cols_no_key))

        mm_rows = []
        shared_keys = sorted(set(res_keyed.index) & set(gt_keyed.index))
        for k in shared_keys:
            rrow = res_keyed.loc[k, cols_no_key]
            trow = gt_keyed.loc[k, cols_no_key]
            if isinstance(rrow, pd.DataFrame): rrow = rrow.iloc[0]
            if isinstance(trow, pd.DataFrame): trow = trow.iloc[0]
            for col in cols_no_key:
                rv, tv = rrow[col], trow[col]
                if pd.isna(rv) and pd.isna(tv): continue
                if str(rv) != str(tv):
                    mm_rows.append({key: k, "column": col, "result": rv, "truth": tv})
        mismatched_cells = pd.DataFrame(mm_rows)
        return added_rows, missing_rows, mismatched_cells, missing_cols, extra_cols

    except KeyError:
        return (*rowset_diff(df_res, df_gt, compare_cols), missing_cols, extra_cols)

# ------------ Run ------------
run_dir = RUN_DIR or latest_run_dir()
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
outdir = Path("results") / f"comparisons_{timestamp}"
outdir.mkdir(parents=True, exist_ok=True)

gt_files = sorted(GROUND_DIR.glob("q*_cat3_table.csv"))
if not gt_files:
    raise FileNotFoundError(f"No ground-truth CSVs found in {GROUND_DIR}")

summary_rows = []

for gt_path in gt_files:
    qn = parse_q_number(gt_path.name)
    if qn is None:
        continue

    res_path = match_result_file(run_dir, qn)
    if res_path is None or not res_path.exists():
        gt_df = pd.read_csv(gt_path)
        summary_rows.append({
            "question": f"q{qn}",
            "result_file": "",
            "ground_truth_file": str(gt_path),
            "rows_result": 0,
            "rows_truth": gt_df.shape[0],
            "cols_result": 0,
            "cols_truth": gt_df.shape[1],
            "added_rows": 0,
            "missing_rows": gt_df.shape[0],
            "mismatched_cells": 0,
            "missing_columns": gt_df.shape[1],  # all missing
            "extra_columns": 0,
            "exact_match": False,
            "note": "Result file not found"
        })
        continue

    try:
        df_res = load_csv(res_path)
        df_gt  = load_csv(gt_path)

        added, missing, mismatched, miss_cols, extra_cols = diff_two_tables(df_res, df_gt)

        # Save per-question artifacts
        added.to_csv(outdir / f"q{qn}_added.csv", index=False, encoding="utf-8")
        missing.to_csv(outdir / f"q{qn}_missing.csv", index=False, encoding="utf-8")
        mismatched.to_csv(outdir / f"q{qn}_mismatched_cells.csv", index=False, encoding="utf-8")
        pd.DataFrame({"missing_columns": miss_cols}).to_csv(outdir / f"q{qn}_missing_columns.csv", index=False, encoding="utf-8")
        pd.DataFrame({"extra_columns": extra_cols}).to_csv(outdir / f"q{qn}_extra_columns.csv", index=False, encoding="utf-8")

        exact = (not miss_cols and not extra_cols and added.empty and missing.empty and mismatched.empty)

        summary_rows.append({
            "question": f"q{qn}",
            "result_file": str(res_path),
            "ground_truth_file": str(gt_path),
            "rows_result": df_res.shape[0],
            "rows_truth": df_gt.shape[0],
            "cols_result": df_res.shape[1],
            "cols_truth": df_gt.shape[1],
            "added_rows": int(added.shape[0]) if not added.empty else 0,
            "missing_rows": int(missing.shape[0]) if not missing.empty else 0,
            "mismatched_cells": int(mismatched.shape[0]) if not mismatched.empty else 0,
            "missing_columns": len(miss_cols),
            "extra_columns": len(extra_cols),
            "exact_match": bool(exact),
            "note": ""
        })
    except Exception as e:
        summary_rows.append({
            "question": f"q{qn}",
            "result_file": str(res_path),
            "ground_truth_file": str(gt_path),
            "rows_result": None,
            "rows_truth": None,
            "cols_result": None,
            "cols_truth": None,
            "added_rows": None,
            "missing_rows": None,
            "mismatched_cells": None,
            "missing_columns": None,
            "extra_columns": None,
            "exact_match": False,
            "note": f"ERROR: {e}"
        })

summary_df = pd.DataFrame(summary_rows)
outdir.mkdir(parents=True, exist_ok=True)
summary_df.to_csv(outdir / "summary.csv", index=False, encoding="utf-8")

print(f"Compared against ground truths in: {GROUND_DIR}")
print(f"Run compared: {run_dir}")
print(f"Wrote per-question diffs and summary to: {outdir}")
