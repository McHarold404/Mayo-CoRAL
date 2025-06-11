#!/usr/bin/env python3


''' 
Running our command:
python evaluate_NewAPI.py \   --doc "NCT02799602_Hussain_ARASENS_JCO'23.pdf" \    --pp_file "file_search/NCT02799602_Hussain_ARASENS_JCO'23/pp_output.txt" \
    --gold_csv "GoldTable.csv" \
    --prompt "prompts/evaluation_prompt.txt" \
    --model gpt
'''

'''
Change the paths of the files to store to the intended folder. 
Right now the file "evaluation_results", which contains the evaluation results, is stored in the "Code" repo.

'''

"""
evaluate_NewAPI.py
Evaluate post-processed LLM output against a gold CSV.

Reads the API key from a .env file (default: .env in the working directory)
or from the --env argument, or via --key, or from existing environment vars.

Example (GPT):
    python evaluate_NewAPI.py \
        --doc "NCT00104715_Gravis_GETUG_EU'15.pdf" \
        --pp_file "file_search/NCT00104715_Gravis_GETUG_EU'15/pp_output.txt" \
        --gold_csv "GoldTable.csv" \
        --prompt "prompts/evaluation_prompt.txt" \
        --model gpt
"""

import os
import re
import argparse
import pandas as pd
from pathlib import Path

# ────────────── dotenv first ──────────────
try:
    from dotenv import load_dotenv
except ImportError as exc:
    raise SystemExit("❌ python-dotenv not installed - run `pip install python-dotenv`") from exc


def calculate_accuracy_and_append(file_path: str) -> None:
    """
    Extended accuracy calculator with three outputs:
    
    1. Overall Accuracy
    2. Non-null Gold Accuracy
    3. A new file containing only non-null gold lines:
       "evaluation_results_non_null_only.txt" in the same folder as file_path.
    """
    NULL_TOKENS = {"nan", "not present", "n/a", "na", ""}
    value_pattern = re.compile(r":\s*(.*?)\s*vs\s*(.*?)\s*=>", re.IGNORECASE)

    correct = total = 0
    non_null_correct = non_null_total = 0
    non_null_lines = []

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        # 1. Overall accuracy logic
        if "Not Equivalent" in line:
            total += 1
        elif "Equivalent" in line:
            total += 1
            correct += 1

        # 2. Non-null evaluation logic
        match = value_pattern.search(line)
        if match:
            gold_val = match.group(1).strip()
            if gold_val.lower() not in NULL_TOKENS:
                non_null_total += 1
                non_null_lines.append(line)
                if "Equivalent" in line and "Not Equivalent" not in line:
                    non_null_correct += 1

    overall_acc = (correct / total * 100) if total else 0.0
    non_null_acc = (non_null_correct / non_null_total * 100) if non_null_total else 0.0

    summary = (
        f"\nTotal Evaluated Lines: {total}\n"
        f"Equivalent Lines: {correct}\n"
        f"Overall Accuracy: {overall_acc:.2f}%\n\n"
        f"Non-null Gold Lines: {non_null_total}\n"
        f"Non-null Correct Lines: {non_null_correct}\n"
        f"Non-null Accuracy: {non_null_acc:.2f}%"
    )

    # Append summary to the original file
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(summary)

    # Determine the output path for non-null lines
    output_dir = os.path.dirname(file_path)
    output_path = os.path.join(output_dir, "evaluation_results_non_null_only.txt")

    # Write non-null lines to new file
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(non_null_lines)


def load_env_file(path: str | Path | None = None) -> None:
    """
    Load environment variables from `.env` (or a custom path).
    Ignores the call if the file is missing.
    """
    env_path = Path(path) if path else Path(".env")
    if env_path.is_file():
        load_dotenv(env_path)
        print(f"DEBUG ⓪ Loaded env file: {env_path}")  # 🔴 DEBUG – REMOVE
    else:
        print(f"DEBUG ⓪ No .env file found at {env_path}")  # 🔴 DEBUG – REMOVE


# ────────────── model helpers ──────────────
from model_inference.gpt import ask_chatgpt
from model_inference.gemini import ask_gemini


def get_model_function(model_type: str):
    if model_type.lower() == "gemini":
        return ask_gemini
    if model_type.lower() == "gpt":
        return ask_chatgpt
    raise ValueError(f"Unsupported model type: {model_type}")


# ────────────── text utilities ──────────────
def extract_columns(text: str) -> dict:
    """Return {column: value} from `Column :: Value` lines."""
    pattern = r"^(.*?)\s*::\s*(.*)$"
    return {k.strip(): v.strip() for k, v in re.findall(pattern, text, re.MULTILINE)}


def build_unified_mapping(gold: dict, preds: dict) -> str:
    """Line per column:  Column: gold, pred"""
    return "\n".join(f"{k}: {gold.get(k, 'not present')}, {preds.get(k)}" for k in preds)


# ────────────── key activator ──────────────
def activate_key(model_type: str, api_key: str) -> None:
    """Expose `api_key` to the correct SDK *and* env."""
    if not api_key:
        raise ValueError("Empty API key")

    if model_type.lower() == "gpt":
        os.environ["OPENAI_API_KEY"] = api_key
        import openai
        openai.api_key = api_key
    elif model_type.lower() == "gemini":
        os.environ["GOOGLE_API_KEY"] = api_key
        import google.generativeai as genai
        genai.configure(api_key=api_key)
    else:
        raise ValueError(f"Unsupported model: {model_type}")

    # 🔴 DEBUG – REMOVE
    short = api_key[:5] + "..." if len(api_key) > 8 else api_key
    print(f"DEBUG ➊ Env + SDK ready for {model_type.upper()}: {short}")


# ────────────── main evaluation logic ──────────────
def evaluate(document_name: str,
             pp_text: str,
             gold_csv: str,
             prompt_path: str,
             model_type: str,
             api_key: str) -> str:
    preds = extract_columns(pp_text)

    df = pd.read_csv(gold_csv)
    row = df.loc[df['Document Name'] == document_name]
    if row.empty:
        raise ValueError(f"No gold labels for document: {document_name}")
    gold = row.iloc[0].to_dict()

    mapping = build_unified_mapping({k: gold[k] for k in preds if k in gold}, preds)

    activate_key(model_type, api_key)

    model_fn = get_model_function(model_type)
    return model_fn(prompt_path=prompt_path, text=mapping)


# ────────────── CLI entrypoint ──────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate post-processed output.")
    parser.add_argument("--doc", required=True)
    parser.add_argument("--pp_file", required=True)
    parser.add_argument("--gold_csv", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--model", choices=["gpt", "gemini"], required=True)
    parser.add_argument("--key", help="API key (overrides .env/env vars)")
    parser.add_argument("--env", help="Path to custom .env file")

    args = parser.parse_args()

    # 1. load .env (if any) before we look for the key
    load_env_file(args.env)

    # 2. resolve key precedence:  --key > env vars from dotenv > existing env
    api_key = (
        args.key or
        os.getenv("OPENAI_API_KEY") or
        os.getenv("GOOGLE_API_KEY")
    )
    if not api_key:
        raise ValueError("No API key found. Supply --key or create a .env with OPENAI_API_KEY=/GOOGLE_API_KEY=")

    with open(args.pp_file, "r", encoding="utf-8") as fp:
        pp_text = fp.read()

    try:
        result = evaluate(
            document_name=args.doc,
            pp_text=pp_text,
            gold_csv=args.gold_csv,
            prompt_path=args.prompt,
            model_type=args.model,
            api_key=api_key
        )
        print("\n——— EVALUATION RESULT ———\n")
        print(result)

        out = f"evaluation_result_{args.doc.replace(' ', '_')}.txt"
        Path(out).write_text(result, encoding="utf-8")
        print(f"\nSaved to {out}")
        calculate_accuracy_and_append(out)
    except Exception as err:
        print(f"❌ Error: {err}")


if __name__ == "__main__":
    main()


