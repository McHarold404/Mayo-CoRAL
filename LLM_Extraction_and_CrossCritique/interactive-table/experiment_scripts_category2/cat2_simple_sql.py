#!/usr/bin/env python3
"""
CATEGORY 2 QUESTIONS - BASE (vLLM)

SIMPLE SQL RESPONSES ON QUESTIONS THAT REQUIRE AN SQL RESPONSE

Adds:
- Crash-safe resume via progress.jsonl (append per-row) + skip completed rows on restart
- Stable run_id folder (optionally user-set) so reruns can resume into same folder
- model_name used for folder naming (not snapshot dir)
- Overall Relaxed EM metric saved + printed
- Pred SQL execution runs set to 1 (default) via --num-runs (default=1)

Relaxed EM definition (default):
relaxed_em = 1 if (
    (sql_token_jaccard_vs_gt >= relaxed_em_threshold) OR
    (results_equal_exact is True when both executed)
) else 0
"""

import os
import re
import json
import time
import hashlib
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List, Set

from tqdm.auto import tqdm
import pandas as pd

# Optional: SQLAlchemy/DB
try:
    from sqlalchemy import create_engine, text
    HAVE_SQLALCHEMY = True
except Exception:
    HAVE_SQLALCHEMY = False

# Optional: vLLM
try:
    from vllm import LLM, SamplingParams
    HAVE_VLLM = True
except Exception:
    HAVE_VLLM = False

# Optional: dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# ----------------------------------------------------------------------------
# Defaults / ENV
# ----------------------------------------------------------------------------
DB_NAME = os.getenv("CAT2_DB_NAME", "trialsdb")
ENGINE_URI = os.getenv("CAT2_ENGINE_URI", f"postgresql://postgres:5555@localhost:5432/{DB_NAME}")
TABLE_NAME = os.getenv("CAT2_TABLE_NAME", "clinical_trials")
TABLE_FQN = os.getenv("CAT2_TABLE_FQN", 'public."clinical_trials"')

# vLLM defaults (override by env or CLI)
ENV_MODEL = os.getenv("CAT2_MODEL", "").strip()
ENV_TP = os.getenv("CAT2_TP", "").strip()
ENV_GPU_MEM = os.getenv("CAT2_GPU_MEMORY_UTILIZATION", "").strip()
ENV_MAX_LEN = os.getenv("CAT2_MAX_MODEL_LEN", "").strip()
ENV_DTYPE = os.getenv("CAT2_DTYPE", "bfloat16").strip()
ENV_TEMP = os.getenv("CAT2_TEMPERATURE", "0.1").strip()
ENV_MAX_TOKENS = os.getenv("CAT2_MAX_TOKENS", "600").strip()

# Your repo absolute root (used for robust query-cat2.xlsx resolution)
REPO_RUNS_ABS = Path(
    os.getenv(
        "CAT2_RUNS_ABS",
        "/mnt/data1/srchowd3/Mayo-CoRAL/LLM_Extraction_and_CrossCritique/interactive-table/runs"
    )
)


def _candidate_xlsx_paths(cli_xlsx: Optional[str] = None) -> List[Path]:
    out: List[Path] = []
    if cli_xlsx:
        out.append(Path(cli_xlsx).expanduser())

    env_x = os.getenv("CAT2_XLSX", "").strip()
    if env_x:
        out.append(Path(env_x).expanduser())

    out.extend([
        Path("/mnt/data/query-cat2.xlsx"),
        Path("/mnt/data/runs/query-cat2.xlsx"),
        Path("runs/query-cat2.xlsx"),
        Path("../runs/query-cat2.xlsx"),
        REPO_RUNS_ABS / "query-cat2.xlsx",
    ])

    seen = set()
    uniq = []
    for p in out:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        k = str(rp)
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


# ----------------------------------------------------------------------------
# Column reflection / mapping
# ----------------------------------------------------------------------------
engine = None
actual_columns: List[str] = []
normalized_to_actual: Dict[str, str] = {}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def build_column_maps(cols: List[str]) -> Dict[str, str]:
    m: Dict[str, str] = {}
    for c in cols:
        m[norm(c)] = c
        m[norm(c.replace("_", " ").replace(" ", ""))] = c
        m[norm(c.replace(" ", "_"))] = c
    if "nct" in cols and "id" not in cols:
        m["id"] = "nct"
    return m


if HAVE_SQLALCHEMY:
    try:
        engine = create_engine(ENGINE_URI, pool_pre_ping=True)
        with engine.connect() as conn:
            q = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name='clinical_trials'
                ORDER BY ordinal_position
            """)
            actual_columns = [r[0] for r in conn.execute(q).fetchall()]
        normalized_to_actual = build_column_maps(actual_columns)
    except Exception as e:
        print(f"[WARN] DB reflection failed: {e}")


fallback_cols = [
    "id", "nct", "pubmed_id", "trial_name", "author", "year", "trial_phase", "number_of_arms",
    "total_sample_size", "publication_type", "cancer_type", "treatment_regimen", "ici_name",
    "ici_class", "therapy_modality", "combination_type", "control_regimen", "control_type",
    "lines_of_treatment", "clinical_setting_in_relation_to_surgery", "primary_endpoint",
    "primary_endpoint_is_multiple_or_composite", "secondary_endpoint", "pdl1_inclusion",
    "other_biomarker_inclusion", "follow_up_type", "follow_up_duration_overall_months",
    "follow_up_duration_rx_months", "follow_up_duration_control_months", "included_in_ma",
    "therapy_type", "clinical_setting"
]
if not actual_columns:
    actual_columns = fallback_cols[:]
    normalized_to_actual = build_column_maps(actual_columns)


# ----------------------------------------------------------------------------
# Optional definitions (best-effort)
# ----------------------------------------------------------------------------
def_roots = [
    Path("/mnt/data/definitions_folder"),
    Path("runs/definitions_folder"),
    Path("../runs/definitions_folder"),
    Path("./definitions_folder"),
    Path("/mnt/data"),
    Path("runs"),
    Path(".."),
    REPO_RUNS_ABS / "definitions_folder",
    Path("/mnt/data1/runs/definitions_folder"),
]
def_names = [
    "definitions - aim2 - filter concise.txt",
    "definitions - aim2 - column concise.txt",
]
def_paths: Dict[str, Optional[Path]] = {}
for name in def_names:
    found = None
    for root in def_roots:
        candidate = root / name
        if candidate.exists():
            found = candidate
            break
    def_paths[name] = found


def read_text_or_empty(p: Optional[Path]) -> str:
    if p is None:
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


definitions_filter = read_text_or_empty(def_paths["definitions - aim2 - filter concise.txt"])
definitions_column = read_text_or_empty(def_paths["definitions - aim2 - column concise.txt"])


# ----------------------------------------------------------------------------
# Prompt construction
# ----------------------------------------------------------------------------
def make_system_context() -> str:
    schema_block = (
        f"# DATABASE\n"
        f"- Engine: PostgreSQL\n"
        f'- Table: {TABLE_FQN}\n'
        f"- Columns (use EXACT spelling below and always double-quote):\n  - " + "\n  - ".join(actual_columns)
    )

    definitions_block = ""
    if definitions_filter.strip() or definitions_column.strip():
        definitions_block = (
            "\n\n# DEFINITIONS (concise)\n"
            "## Filters\n" + (definitions_filter.strip() or "[missing]") + "\n\n"
            "## Columns\n" + (definitions_column.strip() or "[missing]")
        )

    guardrails = r"""
# REQUIREMENTS
- Use ONLY the columns listed above and reference them with double quotes, e.g., "cancer_type".
- Qualify the table as public."clinical_trials".
- When counting trials, use COUNT(DISTINCT "nct"). Do NOT use id.
- If PD-1 is mentioned, map to "PD1" for "ici_class" (no dash).
- Prefer exact equality for enumerated values; use ILIKE with %...% for free text.
- SELECT queries only; no DDL/DML.
- Unless the question explicitly asks for a count or summary statistic, return rows and always include:
  "nct", "author", "year", "pubmed_id".

# OUTPUT FORMAT (strict JSON)
Return ONLY a JSON object with keys:
- "sql": string (runnable PostgreSQL SELECT)
- "answer": string (<= 1–2 sentences)
- "assumptions": string (empty if none)
"""
    return f"{schema_block}{definitions_block}{guardrails}"


def make_user_prompt(question: str) -> str:
    return (
        f"You are an expert clinical-trials data analyst. "
        f"Write a PostgreSQL query on table {TABLE_FQN} to answer the question.\n\n"
        f"QUESTION:\n{question}\n"
    )


# ----------------------------------------------------------------------------
# JSON parsing helpers
# ----------------------------------------------------------------------------
def strip_code_fences(s: str) -> str:
    s = str(s).strip()
    if s.startswith("```"):
        s = s[s.find("\n") + 1:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


def parse_json_safe(text: str) -> Optional[Dict[str, Any]]:
    if text is None:
        return None
    raw = strip_code_fences(text)
    try:
        return json.loads(raw)
    except Exception:
        pass
    try:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end+1])
    except Exception:
        pass
    return None


# ----------------------------------------------------------------------------
# SQL fix-ups and execution (with retries)
# ----------------------------------------------------------------------------
def qualify_table(sql: str) -> str:
    def repl(m):
        return m.group(0).replace("clinical_trials", 'public."clinical_trials"')
    return re.sub(r'(?i)(from|join)\s+clinical_trials\b', repl, sql)


def try_map_column(name: str) -> Optional[str]:
    key = norm(name)
    target = normalized_to_actual.get(key)
    if target:
        return f'"{target}"'
    if key == "id" and "nct" in actual_columns:
        return '"nct"'
    return None


def repair_sql_columns(sql: str, err_msg: str) -> Optional[str]:
    m = re.search(r'column\s+"?([A-Za-z0-9_ ]+)"?\s+does not exist', err_msg, flags=re.I)
    if not m:
        m2 = re.search(
            r'Perhaps you meant to reference the column\s+"?clinical_trials\.([A-Za-z0-9_ ]+)"?',
            err_msg, flags=re.I
        )
        if not m2:
            return None
        missing = m2.group(1)
    else:
        missing = m.group(1)

    mapped = try_map_column(missing)
    if not mapped:
        return None

    pattern = r'\b' + re.escape(missing) + r'\b'
    fixed = re.sub(pattern, mapped, sql)
    return fixed


def is_select_only(sql: str) -> bool:
    s = re.sub(r"/\*.*?\*/", "", (sql or ""), flags=re.S).strip().lower()
    if not (s.startswith("select") or s.startswith("with")):
        return False
    forbidden = ["insert ", "update ", "delete ", "drop ", "alter ", "create ", "truncate "]
    return not any(x in s for x in forbidden)


def execute_with_retries(engine, sql: str, max_retries: int = 3) -> Tuple[str, Optional[pd.DataFrame], Optional[str], str, float]:
    if engine is None:
        return "skipped", None, "No DB engine available", sql, 0.0

    attempt_sql = qualify_table(sql or "")
    last_err = None
    t0 = time.perf_counter()

    for _ in range(max_retries):
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(attempt_sql), conn)
            latency = (time.perf_counter() - t0) * 1000.0
            return "ok", df, None, attempt_sql, latency
        except Exception as e:
            last_err = str(e)
            if "does not exist" in last_err and "column" in last_err.lower():
                fixed = repair_sql_columns(attempt_sql, last_err)
                if fixed and fixed != attempt_sql:
                    attempt_sql = fixed
                    continue
            break

    latency = (time.perf_counter() - t0) * 1000.0
    return "error", None, last_err, attempt_sql, latency


# ----------------------------------------------------------------------------
# Metrics helpers
# ----------------------------------------------------------------------------
def stable_hash_df(df: Optional[pd.DataFrame]) -> str:
    if df is None:
        return ""
    try:
        df2 = df.copy()
        df2.columns = [str(c) for c in df2.columns]
        df2 = df2.reindex(sorted(df2.columns), axis=1)
        for c in df2.columns:
            df2[c] = df2[c].astype(str)
        df2 = df2.sort_values(list(df2.columns)).reset_index(drop=True)
        csv_bytes = df2.to_csv(index=False).encode("utf-8")
        return hashlib.md5(csv_bytes).hexdigest()
    except Exception:
        return f"shape:{getattr(df, 'shape', None)}|cols:{list(getattr(df, 'columns', []))}"


def token_jaccard(a: str, b: str) -> float:
    A = set(re.findall(r"[a-z0-9_]+", (a or "").lower()))
    B = set(re.findall(r"[a-z0-9_]+", (b or "").lower()))
    if not A and not B:
        return 1.0
    return len(A & B) / max(1, len(A | B))


def column_overlap_ratio(df_pred: Optional[pd.DataFrame], df_gt: Optional[pd.DataFrame]) -> Optional[float]:
    if df_pred is None or df_gt is None:
        return None
    A = {str(c).lower() for c in df_pred.columns}
    B = {str(c).lower() for c in df_gt.columns}
    if not A and not B:
        return 1.0
    return len(A & B) / max(1, len(A | B))


def set_metrics_on_nct(df_pred: Optional[pd.DataFrame], df_gt: Optional[pd.DataFrame]) -> Dict[str, Any]:
    def find_nct_col(cols: List[str]) -> Optional[str]:
        for c in cols:
            if norm(c) == "nct":
                return c
        return None

    out = {"nct_precision": None, "nct_recall": None, "nct_f1": None, "nct_jaccard": None}
    if df_pred is None or df_gt is None:
        return out

    pred_cols = [str(c) for c in df_pred.columns]
    gt_cols = [str(c) for c in df_gt.columns]
    c_pred = find_nct_col(pred_cols)
    c_gt = find_nct_col(gt_cols)
    if not c_pred or not c_gt:
        return out

    S = set(df_pred[c_pred].astype(str).dropna().tolist())
    T = set(df_gt[c_gt].astype(str).dropna().tolist())
    if not S and not T:
        return {"nct_precision": 1.0, "nct_recall": 1.0, "nct_f1": 1.0, "nct_jaccard": 1.0}

    tp = len(S & T)
    precision = tp / max(1, len(S))
    recall = tp / max(1, len(T))
    f1 = (2 * precision * recall) / max(1e-12, (precision + recall)) if (precision + recall) > 0 else 0.0
    jacc = len(S & T) / max(1, len(S | T))
    return {"nct_precision": precision, "nct_recall": recall, "nct_f1": f1, "nct_jaccard": jacc}


# ----------------------------------------------------------------------------
# Excel helpers
# ----------------------------------------------------------------------------
def autodetect_columns(df: pd.DataFrame) -> Tuple[str, Optional[str]]:
    qcol = next((c for c in df.columns if "query" in c.lower() or "question" in c.lower()), df.columns[0])
    gcol = next((c for c in df.columns if "sql" in c.lower() or "ground" in c.lower() or "postgres" in c.lower()), None)
    if gcol is None and len(df.columns) > 1:
        for c in df.columns[1:]:
            if df[c].astype(str).str.contains(r"\bselect\b", flags=re.I, na=False).any():
                gcol = c
                break
    return qcol, gcol


# ----------------------------------------------------------------------------
# vLLM: build prompt + generate
# ----------------------------------------------------------------------------
def build_chat_prompt(model_id_or_path: str, system_text: str, user_text: str) -> str:
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(model_id_or_path, trust_remote_code=True)
        msgs = [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}]
        if hasattr(tok, "apply_chat_template"):
            return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    except Exception:
        pass
    return f"<|system|>\n{system_text}\n<|user|>\n{user_text}\n<|assistant|>\n"


def generate_sql_json_with_vllm(llm: "LLM", prompt: str, temperature: float, max_tokens: int) -> Dict[str, Any]:
    sp = SamplingParams(
        temperature=temperature,
        max_tokens=max_tokens,
        stop=["```", "<|eot_id|>", "<|end_of_text|>", "<|im_end|>"],
    )
    out = llm.generate([prompt], sp)
    text_out = out[0].outputs[0].text if out and out[0].outputs else ""
    data = parse_json_safe(text_out) or {}
    return {
        "sql": str(data.get("sql", "")).strip(),
        "answer": str(data.get("answer", "")).strip(),
        "assumptions": str(data.get("assumptions", "")).strip(),
        "raw_text": text_out,
    }


# ----------------------------------------------------------------------------
# Resume helpers
# ----------------------------------------------------------------------------
def load_completed_indices(progress_jsonl: Path) -> Set[int]:
    done: Set[int] = set()
    if not progress_jsonl.exists():
        return done
    try:
        with progress_jsonl.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if "row_index" in obj:
                        done.add(int(obj["row_index"]))
                except Exception:
                    continue
    except Exception:
        return done
    return done


def append_jsonl(progress_jsonl: Path, obj: Dict[str, Any]) -> None:
    with progress_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def safe_slug(s: str, max_len: int = 60) -> str:
    s = (s or "").strip()
    s = re.sub(r"^models--", "", s)
    s = s.replace("--", "/")
    s = re.sub(r"[^A-Za-z0-9_.-/]+", "_", s)
    s = s.strip("_")
    return s[:max_len] if len(s) > max_len else s


def _get(lst: List[Any], i: int, default=None):
    return lst[i] if i < len(lst) else default


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=(ENV_MODEL or "Qwen/Qwen2.5-7B-Instruct"),
                        help="HF repo id or local snapshot path for vLLM.")
    parser.add_argument("--model-name", type=str, default="",
                        help="Name used for output folder + reporting (e.g., Qwen/Qwen2.5-7B-Instruct).")
    parser.add_argument("--run-id", type=str, default="",
                        help="If set, outputs go to results/<run-id>/ and resumes there.")
    parser.add_argument("--xlsx", type=str, default="",
                        help="Path to query-cat2.xlsx. If not provided, uses CAT2_XLSX / auto-discovery.")
    parser.add_argument("--limit", type=int, default=int(os.getenv("NUM_QUESTIONS", "0") or 0),
                        help="Number of questions to run. If 0, run all rows.")
    parser.add_argument("--tp", type=int, default=int(ENV_TP) if ENV_TP.isdigit() else 1,
                        help="tensor_parallel_size for vLLM.")
    parser.add_argument("--gpu-mem-util", type=float,
                        default=float(ENV_GPU_MEM) if ENV_GPU_MEM else 0.90,
                        help="vLLM gpu_memory_utilization.")
    parser.add_argument("--max-model-len", type=int,
                        default=int(ENV_MAX_LEN) if ENV_MAX_LEN.isdigit() else 8192,
                        help="vLLM max_model_len.")
    parser.add_argument("--dtype", type=str, default=ENV_DTYPE,
                        help="bfloat16 / float16 / auto.")
    parser.add_argument("--temperature", type=float, default=float(ENV_TEMP),
                        help="Sampling temperature.")
    parser.add_argument("--max-tokens", type=int, default=int(ENV_MAX_TOKENS),
                        help="Max new tokens for model output.")
    parser.add_argument("--results-root", type=str, default="results",
                        help="Root output folder.")
    parser.add_argument("--run-sql", action="store_true",
                        help="Actually execute SQL against Postgres (requires SQLAlchemy).")
    parser.add_argument("--num-runs", type=int, default=1,
                        help="Number of times to execute the predicted SQL (default: 1).")
    parser.add_argument("--save-every", type=int, default=10,
                        help="Write evaluation_partial.csv every N completed rows.")
    parser.add_argument("--relaxed-em-threshold", type=float, default=0.70,
                        help="Threshold on SQL token Jaccard to count as relaxed EM match.")
    args = parser.parse_args()

    if not HAVE_VLLM:
        raise RuntimeError("vLLM not installed in this environment (pip install vllm).")

    # Locate xlsx
    candidates = _candidate_xlsx_paths(args.xlsx.strip() or None)
    xlsx_path = next((p for p in candidates if p.exists()), None)
    if not xlsx_path:
        print("\n[ERROR] Could not find query-cat2.xlsx.")
        print(f"  cwd: {Path.cwd()}")
        print("  searched:")
        for p in candidates:
            print(f"   - {p}")
        raise FileNotFoundError("Could not find query-cat2.xlsx (set --xlsx or CAT2_XLSX).")

    df_in = pd.read_excel(xlsx_path)
    qcol, gcol = autodetect_columns(df_in)

    if args.limit and args.limit > 0:
        df_in = df_in.head(args.limit)

    # Model naming (for folder + reporting)
    model_name = args.model_name.strip()
    if not model_name:
        if "/" in args.model and not Path(args.model).exists():
            model_name = args.model
        else:
            model_name = Path(args.model).name
    model_name_slug = safe_slug(model_name, max_len=80).replace("/", "_")

    # Run folder (resume-friendly)
    if args.run_id.strip():
        run_id = args.run_id.strip()
    else:
        ts = time.strftime("%Y%m%d_%H%M%S")
        run_id = f"cat2_sql_{ts}_{model_name_slug}"

    results_dir = Path(args.results_root) / run_id
    results_dir.mkdir(parents=True, exist_ok=True)

    # Stable output filenames inside run folder
    progress_jsonl = results_dir / "progress.jsonl"
    partial_csv = results_dir / "evaluation_partial.csv"
    final_csv = results_dir / "evaluation.csv"
    final_xlsx = results_dir / "evaluation.xlsx"
    summary_json = results_dir / "_summary.json"
    overall_csv = results_dir / "overall_metrics.csv"
    overall_json = results_dir / "overall_metrics.json"

    sqls_root = results_dir / "sql_runs"
    sqls_root.mkdir(parents=True, exist_ok=True)

    completed = load_completed_indices(progress_jsonl)

    print("========================================")
    print("CAT2 SQL (vLLM) - RESUMABLE")
    print(f"Model (load): {args.model}")
    print(f"Model (name): {model_name}")
    print(f"Run ID: {run_id}")
    print(f"Results dir: {results_dir}")
    print(f"tp: {args.tp}")
    print(f"gpu_memory_utilization: {args.gpu_mem_util}")
    print(f"max_model_len: {args.max_model_len}")
    print(f"dtype: {args.dtype}")
    print(f"temperature: {args.temperature}")
    print(f"max_tokens: {args.max_tokens}")
    print(f"DB run enabled: {args.run_sql} (sqlalchemy={HAVE_SQLALCHEMY})")
    print(f"XLSX: {xlsx_path}")
    print(f"Resume: {len(completed)} rows already completed")
    print(f"Pred SQL exec num-runs: {args.num_runs}")
    print("========================================")

    # Build vLLM
    llm = LLM(
        model=args.model,
        tensor_parallel_size=args.tp,
        gpu_memory_utilization=args.gpu_mem_util,
        max_model_len=args.max_model_len,
        dtype=args.dtype,
        enforce_eager=True,
        swap_space=0,
    )

    system_text = make_system_context()

    # In-memory aggregation for final outputs
    records: List[Dict[str, Any]] = []

    # If resuming, load prior records into memory
    if progress_jsonl.exists():
        with progress_jsonl.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and "row_index" in obj and "question" in obj:
                        records.append(obj)
                except Exception:
                    continue

    start = time.time()
    processed_now = 0

    num_runs = max(1, int(args.num_runs))

    for idx, row in tqdm(df_in.iterrows(), total=len(df_in), desc="Questions", unit="q"):
        if int(idx) in completed:
            continue

        question = str(row[qcol]).strip()
        gt_sql = str(row[gcol]).strip() if gcol and gcol in df_in.columns and pd.notna(row[gcol]) else None

        user_text = make_user_prompt(question)
        prompt = build_chat_prompt(args.model, system_text, user_text)
        forced = prompt + "\n\nReturn ONLY the JSON object now.\n{"
        out = llm.generate([forced], sp)


        gen = generate_sql_json_with_vllm(
            llm=llm,
            prompt=prompt,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )

        pred_sql_original = gen.get("sql", "") or ""
        pred_sql_final = pred_sql_original

        if not pred_sql_original.strip():
            pred_sql_original = f"/* empty model output for row {idx} */ SELECT 1;"
        if not is_select_only(pred_sql_original):
            pred_sql_original = f"/* non-SELECT produced; forcing safe query */ SELECT 1;"
        pred_sql_original = qualify_table(pred_sql_original)

        # Execute pred SQL N times (default 1)
        run_statuses, run_errors, run_lat_ms, run_hashes = [], [], [], []
        exec_df_last = None

        per_row_dir = sqls_root / f"row{int(idx):03d}"
        per_row_dir.mkdir(parents=True, exist_ok=True)

        (per_row_dir / "pred_sql_original.sql").write_text(pred_sql_original, encoding="utf-8")

        for r in range(num_runs):
            if args.run_sql and HAVE_SQLALCHEMY:
                status, df_exec, err, final_sql, lat_ms = execute_with_retries(engine, pred_sql_original)
            else:
                status, df_exec, err, final_sql, lat_ms = ("skipped", None, "execution disabled", pred_sql_original, 0.0)

            run_statuses.append(status)
            run_errors.append(err)
            run_lat_ms.append(lat_ms)
            run_hashes.append(stable_hash_df(df_exec) if status == "ok" else "")
            pred_sql_final = final_sql

            if df_exec is not None:
                csv_path = per_row_dir / f"pred_run{r+1}_results.csv"
                df_exec.to_csv(csv_path, index=False)

            if status == "ok":
                exec_df_last = df_exec

        (per_row_dir / "pred_sql_final.sql").write_text(pred_sql_final, encoding="utf-8")

        # determinism not meaningful for 1 run
        if num_runs <= 1:
            deterministic = None
        else:
            ok_runs = [h for (s, h) in zip(run_statuses, run_hashes) if s == "ok" and h]
            deterministic = (len(ok_runs) >= 2 and len(set(ok_runs)) == 1)

        # Ground-truth SQL (once)
        if gt_sql and isinstance(gt_sql, str) and gt_sql.strip():
            gt_sql_q = qualify_table(gt_sql)
            (per_row_dir / "gt_sql.sql").write_text(gt_sql_q, encoding="utf-8")

            if args.run_sql and HAVE_SQLALCHEMY:
                gt_status, gt_df, gt_err, gt_sql_final, gt_lat_ms = execute_with_retries(engine, gt_sql_q, max_retries=1)
            else:
                gt_status, gt_df, gt_err, gt_sql_final, gt_lat_ms = ("skipped", None, "execution disabled", gt_sql_q, 0.0)

            if gt_df is not None:
                (per_row_dir / "gt_results.csv").write_text(gt_df.to_csv(index=False), encoding="utf-8")
        else:
            gt_status, gt_df, gt_err, gt_sql_final, gt_lat_ms = ("skipped", None, None, None, 0.0)

        # Metrics
        results_equal = None
        rowcount_delta = None
        if exec_df_last is not None and gt_df is not None:
            try:
                results_equal = bool(exec_df_last.equals(gt_df))
            except Exception:
                results_equal = False
            rowcount_delta = (len(exec_df_last) - len(gt_df))

        nct_scores = set_metrics_on_nct(exec_df_last, gt_df)
        col_overlap = column_overlap_ratio(exec_df_last, gt_df)
        sql_sim = token_jaccard(pred_sql_original or "", gt_sql or "") if gt_sql else None

        relaxed_sql_score = sql_sim
        relaxed_em = None
        if gt_sql:
            relaxed_em = 1 if (
                (relaxed_sql_score is not None and relaxed_sql_score >= float(args.relaxed_em_threshold)) or
                (results_equal is True)
            ) else 0

        rec = {
            "row_index": int(idx),
            "question": question,
            "model_name": model_name,
            "model_load_path_or_id": args.model,

            "pred_sql_original": pred_sql_original,
            "pred_sql_final": pred_sql_final,
            "pred_answer": gen.get("answer"),
            "pred_assumptions": gen.get("assumptions"),
            "raw_text": gen.get("raw_text"),

            "run1_status": _get(run_statuses, 0), "run1_ms": _get(run_lat_ms, 0), "run1_error": _get(run_errors, 0),
            "run2_status": _get(run_statuses, 1), "run2_ms": _get(run_lat_ms, 1), "run2_error": _get(run_errors, 1),
            "run3_status": _get(run_statuses, 2), "run3_ms": _get(run_lat_ms, 2), "run3_error": _get(run_errors, 2),
            "deterministic_across_runs": deterministic,
            "pred_result_rows_last_ok": (None if exec_df_last is None else int(len(exec_df_last))),

            "ground_truth_sql": gt_sql,
            "ground_truth_sql_final": gt_sql_final,
            "ground_truth_exec_status": gt_status,
            "ground_truth_ms": gt_lat_ms,
            "ground_truth_error": gt_err,
            "ground_truth_result_rows": (None if gt_df is None else int(len(gt_df))),

            "results_equal_exact": results_equal,
            "rowcount_delta_pred_minus_gt": rowcount_delta,
            "column_overlap_ratio": col_overlap,

            "nct_precision": nct_scores.get("nct_precision"),
            "nct_recall": nct_scores.get("nct_recall"),
            "nct_f1": nct_scores.get("nct_f1"),
            "nct_jaccard": nct_scores.get("nct_jaccard"),

            "sql_token_jaccard_vs_gt": sql_sim,

            "relaxed_em_threshold": float(args.relaxed_em_threshold),
            "relaxed_sql_score": relaxed_sql_score,
            "relaxed_em": relaxed_em,

            "row_artifacts_dir": str(per_row_dir),
        }

        # Per-row manifest (debug)
        (per_row_dir / "manifest.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")

        # Append to progress (CRASH SAFE)
        append_jsonl(progress_jsonl, rec)

        # Update in-memory tracking
        records.append(rec)
        completed.add(int(idx))
        processed_now += 1

        # Periodic partial CSV write
        if args.save_every > 0 and (processed_now % int(args.save_every) == 0):
            try:
                pd.DataFrame.from_records(records).to_csv(partial_csv, index=False)
            except Exception:
                pass

    elapsed = time.time() - start

    # Final outputs
    df_out = pd.DataFrame.from_records(records)
    df_out.to_csv(final_csv, index=False)

    # XLSX (optional) - requires xlsxwriter
    try:
        with pd.ExcelWriter(final_xlsx, engine="xlsxwriter") as writer:
            df_out.to_excel(writer, index=False, sheet_name="evaluation")
            meta = pd.DataFrame({
                "key": [
                    "run_id", "xlsx_path", "have_sqlalchemy", "run_sql", "engine_uri", "table_fqn",
                    "reflected_columns", "runtime_seconds", "timestamp", "model_name", "model_load",
                    "tp", "gpu_mem_util", "max_model_len", "dtype", "temperature", "max_tokens",
                    "row_artifacts_dir", "relaxed_em_threshold", "num_runs"
                ],
                "value": [
                    run_id,
                    str(xlsx_path),
                    str(HAVE_SQLALCHEMY),
                    str(args.run_sql),
                    ENGINE_URI,
                    TABLE_FQN,
                    ", ".join(actual_columns),
                    f"{elapsed:.2f}",
                    time.strftime("%Y%m%d_%H%M%S"),
                    model_name,
                    args.model,
                    str(args.tp),
                    str(args.gpu_mem_util),
                    str(args.max_model_len),
                    str(args.dtype),
                    str(args.temperature),
                    str(args.max_tokens),
                    str(sqls_root),
                    str(args.relaxed_em_threshold),
                    str(num_runs),
                ]
            })
            meta.to_excel(writer, index=False, sheet_name="meta")
    except Exception as e:
        print(f"[WARN] Could not write XLSX ({e}). CSV is written at: {final_csv}")

    def _mean(series_like):
        if series_like is None:
            return None
        s = pd.to_numeric(series_like, errors="coerce").dropna()
        if len(s) == 0:
            return None
        return float(s.mean())

    # Overall metrics (robust to missing run2/run3)
    overall = {
        "rows_total_in_input": int(len(df_in)),
        "rows_completed": int(len(df_out)),
        "ok_rate_run1": float((df_out["run1_status"] == "ok").mean()) if "run1_status" in df_out else None,
        "ok_rate_run2": float((df_out["run2_status"] == "ok").mean()) if "run2_status" in df_out and df_out["run2_status"].notna().any() else None,
        "ok_rate_run3": float((df_out["run3_status"] == "ok").mean()) if "run3_status" in df_out and df_out["run3_status"].notna().any() else None,
        "avg_run1_ms": _mean(df_out.get("run1_ms")),
        "avg_run2_ms": _mean(df_out["run2_ms"]) if "run2_ms" in df_out and df_out["run2_ms"].notna().any() else None,
        "avg_run3_ms": _mean(df_out["run3_ms"]) if "run3_ms" in df_out and df_out["run3_ms"].notna().any() else None,
        "determinism_rate": float(pd.to_numeric(df_out.get("deterministic_across_runs"), errors="coerce").dropna().astype(bool).mean())
        if "deterministic_across_runs" in df_out and pd.to_numeric(df_out["deterministic_across_runs"], errors="coerce").notna().any()
        else None,
        "results_equal_rate": float(df_out["results_equal_exact"].fillna(False).astype(bool).mean()) if "results_equal_exact" in df_out else None,
        "avg_rowcount_delta": _mean(df_out.get("rowcount_delta_pred_minus_gt")),
        "avg_column_overlap_ratio": _mean(df_out.get("column_overlap_ratio")),
        "avg_sql_token_jaccard_vs_gt": _mean(df_out.get("sql_token_jaccard_vs_gt")),
        "avg_nct_precision_macro": _mean(df_out.get("nct_precision")),
        "avg_nct_recall_macro": _mean(df_out.get("nct_recall")),
        "avg_nct_f1_macro": _mean(df_out.get("nct_f1")),
        "avg_nct_jaccard_macro": _mean(df_out.get("nct_jaccard")),
        "relaxed_em_threshold": float(args.relaxed_em_threshold),
        "relaxed_em_rate": float(pd.to_numeric(df_out.get("relaxed_em"), errors="coerce").dropna().mean()) if "relaxed_em" in df_out else None,
        "runtime_seconds": float(elapsed),
        "num_runs": int(num_runs),
    }

    # Save overall
    pd.DataFrame([overall]).to_csv(overall_csv, index=False)
    overall_json.write_text(json.dumps(overall, indent=2), encoding="utf-8")

    # Summary
    summary = {
        "run_id": run_id,
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "xlsx_path": str(xlsx_path),
        "engine_uri": ENGINE_URI,
        "table": TABLE_FQN,
        "have_sqlalchemy": HAVE_SQLALCHEMY,
        "run_sql": args.run_sql,
        "rows_completed": int(len(df_out)),
        "results_dir": str(results_dir),
        "evaluation_csv": str(final_csv),
        "evaluation_xlsx": str(final_xlsx),
        "progress_jsonl": str(progress_jsonl),
        "overall": overall,
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Print summary including relaxed EM
    print("\n--- Run Summary ---")
    print(f"Artifacts folder: {results_dir}")
    print(f"Saved progress JSONL: {progress_jsonl}")
    print(f"Saved CSV: {final_csv}")
    print(f"Saved XLSX: {final_xlsx} (if engine available)")
    print(f"Completed rows: {len(df_out)} / {len(df_in)}")
    print(f"Runtime: {elapsed:.2f}s")

    print("\n--- Overall Metrics ---")
    for k in [
        "rows_completed",
        "ok_rate_run1", "ok_rate_run2", "ok_rate_run3",
        "results_equal_rate",
        "avg_sql_token_jaccard_vs_gt",
        "relaxed_em_threshold",
        "relaxed_em_rate",
        "runtime_seconds",
        "num_runs",
    ]:
        v = overall.get(k)
        if v is None:
            vv = "NA"
        elif isinstance(v, float):
            vv = f"{v:.4f}"
        else:
            vv = str(v)
        print(f"{k:>28}: {vv}")


if __name__ == "__main__":
    main()
