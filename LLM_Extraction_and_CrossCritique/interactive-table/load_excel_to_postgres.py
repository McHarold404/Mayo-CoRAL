#!/usr/bin/env python3
"""
Load an Excel file into PostgreSQL as a table (default: public.clinical_trials).

Features:
- Reads .xlsx with pandas/openpyxl
- Cleans column names to SQL-friendly identifiers (or preserve with --preserve-columns)
- Creates schema if missing
- Writes via SQLAlchemy using chunked inserts
- Basic dtype mapping to reasonable Postgres types

Usage:
  python load_excel_to_postgres.py \
    --xlsx /path/to/ITABLE_iotox.xlsx.xlsx \
    --table clinical_trials \
    --schema public \
    --if-exists replace

You can also pass ENGINE_URI via env:
  export CAT2_ENGINE_URI="postgresql://postgres:5555@localhost:5432/trialsdb"
"""

import argparse
import os
import re
from typing import Dict, Optional

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.types import (
    Text, BigInteger, Float, Boolean, DateTime
)


def clean_identifier(name: str) -> str:
    """
    Convert arbitrary Excel column header -> safe SQL identifier.
    Example: "Total Sample Size" -> "total_sample_size"
    """
    s = str(name).strip()
    s = s.replace("\n", " ").replace("\r", " ")
    s = s.lower()
    s = re.sub(r"[^\w]+", "_", s)       # non [a-z0-9_] -> _
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "col"
    # Postgres identifiers cannot start with a digit unless quoted; avoid that:
    if re.match(r"^\d", s):
        s = f"c_{s}"
    return s


def make_unique(cols):
    seen = {}
    out = []
    for c in cols:
        if c not in seen:
            seen[c] = 0
            out.append(c)
        else:
            seen[c] += 1
            out.append(f"{c}__{seen[c]}")
    return out


def infer_sqlalchemy_types(df: pd.DataFrame) -> Dict[str, object]:
    """
    Provide a conservative dtype map for to_sql.
    Objects -> Text, ints -> BigInteger, floats -> Float, bool -> Boolean, datetimes -> DateTime.
    """
    dtype_map: Dict[str, object] = {}
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_bool_dtype(s):
            dtype_map[col] = Boolean()
        elif pd.api.types.is_integer_dtype(s):
            dtype_map[col] = BigInteger()
        elif pd.api.types.is_float_dtype(s):
            dtype_map[col] = Float()
        elif pd.api.types.is_datetime64_any_dtype(s):
            dtype_map[col] = DateTime()
        else:
            dtype_map[col] = Text()
    return dtype_map


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True, help="Path to Excel file (.xlsx)")
    ap.add_argument("--sheet", default=None, help="Sheet name or index (default: first sheet)")
    ap.add_argument("--schema", default="public", help="Target schema (default: public)")
    ap.add_argument("--table", default="clinical_trials", help="Target table (default: clinical_trials)")
    ap.add_argument("--if-exists", default="replace", choices=["replace", "append", "fail"],
                    help="What to do if table exists (default: replace)")
    ap.add_argument("--engine-uri", default=os.getenv("CAT2_ENGINE_URI", "").strip(),
                    help="SQLAlchemy engine URI. Defaults to CAT2_ENGINE_URI env var.")
    ap.add_argument("--preserve-columns", action="store_true",
                    help="Do not rename columns; use Excel headers as-is (NOT recommended).")
    ap.add_argument("--chunksize", type=int, default=5000, help="Rows per insert batch (default: 5000)")
    ap.add_argument("--create-index-nct", action="store_true",
                    help='Create an index on column "nct" if it exists.')
    args = ap.parse_args()

    if not args.engine_uri:
        raise SystemExit(
            "Missing --engine-uri and CAT2_ENGINE_URI env var not set.\n"
            "Example: export CAT2_ENGINE_URI='postgresql://postgres:5555@localhost:5432/trialsdb'"
        )

    xlsx_path = args.xlsx
    if not os.path.exists(xlsx_path):
        raise SystemExit(f"Excel file not found: {xlsx_path}")

    # Read Excel
    sheet = args.sheet
    # Allow numeric sheet index if user passes "0", "1", etc.
    if sheet is not None and re.fullmatch(r"\d+", str(sheet)):
        sheet = int(sheet)
    df = pd.read_excel(xlsx_path, sheet_name=0 if sheet is None else sheet, engine="openpyxl")

    if df.empty:
        raise SystemExit("Excel loaded but dataframe is empty (no rows).")

    # Normalize column names unless preserving
    if not args.preserve_columns:
        new_cols = [clean_identifier(c) for c in df.columns]
        new_cols = make_unique(new_cols)
        df.columns = new_cols

    # Optional: strip whitespace from object columns (often helps)
    for c in df.columns:
        if df[c].dtype == "object":
            df[c] = df[c].astype(str).replace({"nan": None, "NaN": None}).str.strip()

    engine = create_engine(args.engine_uri, pool_pre_ping=True)

    # Ensure schema exists
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{args.schema}"'))

    # Write table
    dtype_map = infer_sqlalchemy_types(df)

    print("========================================")
    print("LOADING EXCEL -> POSTGRES")
    print(f"XLSX:   {xlsx_path}")
    print(f"SHEET:  {args.sheet if args.sheet is not None else '(default first)'}")
    print(f"DB:     {args.engine_uri}")
    print(f"TABLE:  {args.schema}.{args.table}")
    print(f"ROWS:   {len(df):,}")
    print(f"COLS:   {len(df.columns):,}")
    print(f"MODE:   if_exists={args.if_exists}")
    print("========================================")

    df.to_sql(
        name=args.table,
        con=engine,
        schema=args.schema,
        if_exists=args.if_exists,
        index=False,
        chunksize=args.chunksize,
        method="multi",
        dtype=dtype_map,
    )

    # Optional index on nct
    if args.create_index_nct and "nct" in [c.lower() for c in df.columns]:
        # Find exact column casing
        nct_col = next(c for c in df.columns if c.lower() == "nct")
        ix_name = f"ix_{args.table}_nct"
        with engine.begin() as conn:
            conn.execute(
                text(f'CREATE INDEX IF NOT EXISTS "{ix_name}" ON "{args.schema}"."{args.table}" ("{nct_col}")')
            )
        print(f"[OK] Created/verified index: {ix_name} on {nct_col}")

    # Quick sanity check
    with engine.connect() as conn:
        count = conn.execute(text(f'SELECT COUNT(*) FROM "{args.schema}"."{args.table}"')).scalar_one()
    print(f"[OK] Done. Row count in DB: {count:,}")


if __name__ == "__main__":
    main()
