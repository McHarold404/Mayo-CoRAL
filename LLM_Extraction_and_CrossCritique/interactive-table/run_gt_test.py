# Jupyter cell: run GT SQL from query-cat2.xlsx with auto-fix fallback (column rewrite + retry)

import os
import re
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

# ------------------------
# Config
# ------------------------
ENGINE_URI = os.getenv("CAT2_ENGINE_URI", "postgresql+psycopg2://srchowd3@localhost:5432/trialsdb")

CANDIDATES = [
    Path(os.getenv("CAT2_XLSX", "")).expanduser() if os.getenv("CAT2_XLSX") else None,
    Path("/mnt/data/query-cat2.xlsx"),
    Path("/mnt/data/runs/query-cat2.xlsx"),
    Path("runs/query-cat2.xlsx"),
    Path("../runs/query-cat2.xlsx"),
    Path("/mnt/data1/srchowd3/Mayo-CoRAL/LLM_Extraction_and_CrossCritique/interactive-table/runs/query-cat2.xlsx"),
]
CANDIDATES = [p for p in CANDIDATES if p and p.exists()]
if not CANDIDATES:
    raise FileNotFoundError("Could not find query-cat2.xlsx. Set CAT2_XLSX or place it in runs/ etc.")
XLSX_PATH = CANDIDATES[0]

OUT_DIR = Path("gt_sql_runs_fixed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TABLE_SCHEMA = "public"
TABLE_NAME = "clinical_trials"
TABLE_FQN_QUOTED = 'public."clinical_trials"'  # what we want queries to use

# ------------------------
# Helpers
# ------------------------
def qualify_table(sql: str) -> str:
    """Rewrite FROM/JOIN clinical_trials -> public."clinical_trials"."""
    if not sql:
        return sql
    def repl(m):
        kw = m.group(1)
        return f'{kw} {TABLE_FQN_QUOTED}'
    return re.sub(r'(?i)\b(from|join)\s+clinical_trials\b', repl, sql)

def is_select_only(sql: str) -> bool:
    if not sql:
        return False
    s = re.sub(r"/\*.*?\*/", "", sql, flags=re.S).strip().lower()
    if not (s.startswith("select") or s.startswith("with")):
        return False
    forbidden = ["insert ", "update ", "delete ", "drop ", "alter ", "create ", "truncate "]
    return not any(x in s for x in forbidden)

def pick_cols(df: pd.DataFrame):
    qcol = next((c for c in df.columns if "query" in c.lower() or "question" in c.lower()), df.columns[0])
    gcol = next((c for c in df.columns if "sql" in c.lower() or "ground" in c.lower() or "postgres" in c.lower()), None)
    if gcol is None:
        raise ValueError(f"Could not find a ground-truth SQL column. Columns are: {list(df.columns)}")
    return qcol, gcol

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())

def build_norm_map(cols):
    """Map normalized -> actual column name (best effort)."""
    m = {}
    for c in cols:
        m[norm(c)] = c
        m[norm(c.replace("_", ""))] = c
        m[norm(c.replace("_", " "))] = c
    return m

def extract_undefined_column(err: str):
    """
    Try to pull the missing column name from Postgres errors like:
      column "publication_type" does not exist
    """
    if not err:
        return None
    m = re.search(r'column\s+"([^"]+)"\s+does not exist', err, flags=re.I)
    if m:
        return m.group(1)
    m = re.search(r"column\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+does not exist", err, flags=re.I)
    if m:
        return m.group(1)
    return None

def replace_identifier(sql: str, old: str, new: str) -> str:
    """
    Replace both quoted and unquoted identifier occurrences.
    - "old" -> "new"
    - old   -> new  (word boundary)
    """
    if not sql or not old or not new:
        return sql

    # quoted
    sql2 = re.sub(rf'"{re.escape(old)}"', f'"{new}"', sql)

    # unquoted (only if it looks like an identifier)
    sql2 = re.sub(rf'\b{re.escape(old)}\b', new, sql2)
    return sql2

# ------------------------
# Engine + reflect real schema columns
# ------------------------
engine = create_engine(ENGINE_URI, pool_pre_ping=True)
with engine.connect() as conn:
    cols = [r[0] for r in conn.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = :schema AND table_name = :table
        ORDER BY ordinal_position
    """), {"schema": TABLE_SCHEMA, "table": TABLE_NAME}).fetchall()]

cols_set = set(cols)
norm_map = build_norm_map(cols)

print("DB table columns:", len(cols))
print("First 10 columns:", cols[:10])

# ------------------------
# Known mapping: GT-name -> actual DB column name
# (These are the common mismatches between your older canonical schema and the loaded Excel->DB schema.)
# Add/adjust as needed.
# ------------------------
KNOWN_MAP = {
    # the one that is breaking everything for you right now
    "publication_type": "originial_publication_or_follow_up",

    # common name changes
    "ici_name": "name_of_ici",
    "ici_class": "class_of_ici",
    "therapy_modality": "monotherapy_combination",
    "combination_type": "type_of_combination",
    "control_type": "type_of_control",
    "control_arm": "control_arm",  # already matches
    "clinical_setting_in_relation_to_surgery": "clincal_setting_in_relation_to_surgery",

    "pdl1_inclusion": "is_pd_l1_positivity_inclusion_criteria",
    "other_biomarker_inclusion": "is_any_other_biomarker_used_for_inclusion",
    "follow_up_type": "type_of_follow_up_given",

    "follow_up_duration_overall_months": "follow_up_duration_for_primary_endpoint_s_in_months_overall",
    "follow_up_duration_rx_months": "follow_up_duration_for_primary_endpoint_s_in_months_rx",
    "follow_up_duration_control_months": "follow_up_duration_for_primary_endpoint_s_in_months_control",

    # sometimes GT uses id when table uses nct
    "id": "nct",
}

def pick_replacement(missing_col: str):
    """Return a (replacement, reason) for missing_col or (None, None) if no good guess."""
    if not missing_col:
        return None, None

    # 1) explicit mapping
    if missing_col in KNOWN_MAP and KNOWN_MAP[missing_col] in cols_set:
        return KNOWN_MAP[missing_col], "known_map"

    # 2) normalized fuzzy: if publication_type -> originial_publication_or_follow_up style differences
    nm = norm(missing_col)
    if nm in norm_map:
        cand = norm_map[nm]
        if cand in cols_set:
            return cand, "norm_fuzzy"

    # 3) very light heuristic: find a column containing the same core tokens
    tokens = [t for t in re.split(r"[_\W]+", missing_col.lower()) if t]
    best = None
    best_score = 0
    for c in cols:
        c_low = c.lower()
        score = sum(1 for t in tokens if t and t in c_low)
        if score > best_score:
            best_score = score
            best = c
    if best and best_score >= max(2, len(tokens)//2):  # require some overlap
        return best, f"token_overlap(score={best_score})"

    return None, None

def execute_with_autofix(sql: str, max_fixes: int = 6):
    """
    Try executing SQL. On undefined-column errors, rewrite the SQL and retry.
    Returns: status, df, final_sql, fixes(list), error
    """
    fixes = []
    final_sql = sql

    for attempt in range(max_fixes + 1):
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(final_sql), conn)
            return "ok", df, final_sql, fixes, None
        except Exception as e:
            err = str(e)
            missing = extract_undefined_column(err)
            if not missing:
                return "error", None, final_sql, fixes, err

            repl, reason = pick_replacement(missing)
            if not repl:
                return "error", None, final_sql, fixes, err

            # apply rewrite
            before = final_sql
            final_sql = replace_identifier(final_sql, missing, repl)

            if final_sql == before:
                # avoid infinite loops if replacement didn't change anything
                return "error", None, final_sql, fixes, err

            fixes.append({"missing": missing, "replaced_with": repl, "reason": reason})

    return "error", None, final_sql, fixes, f"Exceeded max_fixes={max_fixes}"

# ------------------------
# Load XLSX
# ------------------------
df_in = pd.read_excel(XLSX_PATH)
qcol, gcol = pick_cols(df_in)

print("\nXLSX:", XLSX_PATH)
print("Question column:", qcol)
print("GT SQL column:", gcol)
print("Rows:", len(df_in))

# ------------------------
# Run GT SQLs with auto-fix
# ------------------------
records = []
for i, row in df_in.iterrows():
    question = str(row[qcol]).strip()
    gt_sql_raw = "" if pd.isna(row[gcol]) else str(row[gcol]).strip()

    gt_sql = qualify_table(gt_sql_raw)

    rec = {
        "row_index": int(i),
        "question": question,
        "gt_sql_original": gt_sql_raw,
        "gt_sql_final": None,
        "status": None,
        "error": None,
        "result_rows": None,
        "results_csv": None,
        "fixes_applied": None,
    }

    if not gt_sql:
        rec["status"] = "skipped"
        rec["error"] = "Empty GT SQL"
        records.append(rec)
        continue

    if not is_select_only(gt_sql):
        rec["status"] = "skipped"
        rec["error"] = "GT SQL not SELECT/WITH-safe"
        records.append(rec)
        continue

    status, df_res, final_sql, fixes, err = execute_with_autofix(gt_sql, max_fixes=6)
    rec["status"] = status
    rec["gt_sql_final"] = final_sql
    rec["fixes_applied"] = fixes

    if status == "ok":
        out_csv = OUT_DIR / f"row{i:03d}_gt_results.csv"
        df_res.to_csv(out_csv, index=False)
        rec["result_rows"] = int(len(df_res))
        rec["results_csv"] = str(out_csv)
    else:
        rec["error"] = err

    records.append(rec)

df_eval = pd.DataFrame.from_records(records)
eval_csv = OUT_DIR / "gt_evaluation_fixed.csv"
df_eval.to_csv(eval_csv, index=False)

print("\nSaved:")
print(" -", eval_csv)
print(" - per-row result CSVs in:", OUT_DIR)

print("\nSummary:")
print(df_eval["status"].value_counts(dropna=False))

# show a few failed rows with their errors + fixes
bad = df_eval[df_eval["status"] == "error"].head(10)[
    ["row_index", "error", "fixes_applied"]
]
print("\nFirst 10 errors (if any):")
print(bad.to_string(index=False))
