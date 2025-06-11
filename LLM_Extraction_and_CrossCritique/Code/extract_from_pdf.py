from __future__ import annotations
"""extract_pipeline_v2.py

Two‑phase pipeline:
1. **Extraction phase** – parallel label‑group queries against a PDF via the
   OpenAI Assistants API (file_search tool). Results saved as **JSON**.
2. **Post‑processing phase** – one GPT‑4o call that digests the JSON and emits
   clean Column :: Final Answer lines, saved to a TXT file.

Both phases report token usage and an estimated USD cost (GPT‑4o June 2025
prices: $0.005 / 1 K input, $0.015 / 1 K output).

---
Usage example:
bash
python extract_from_pdf.py \
  --pdf "training_studies/NCT00104715_Gravis_GETUG_EU'15.pdf" \
  --defs Definitions.csv \
  --model gpt-4o \
  --workers 60

"""

import argparse
import csv
import json
import os
import threading
import time
from collections import defaultdict, OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from textwrap import indent
from typing import Dict, List, Tuple
from pathlib import Path   # alternative, see below
from openai import OpenAI

# ─── Pricing (USD per 1 K tokens) ──────────────────────────────────────────────
GPT4O_INPUT_PRICE = 0.005
GPT4O_OUTPUT_PRICE = 0.015

# ─── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser("Two‑phase PDF extraction + post‑processing pipeline.")
parser.add_argument("--pdf", required=True, help="Path to the PDF file")
parser.add_argument("--defs", required=True, help="Path to Definitions.csv")
parser.add_argument("--model", default="gpt-4o", help="Model for both phases (default gpt-4o)")
parser.add_argument("--workers", type=int, default=4, help="Parallel label groups (default 4)")

args = parser.parse_args()
# ─── Helper Functions ──────────────────────────────────────────────────────
import re
def sanitize_filename(filename):
    return re.sub(r'[\/\\:*?"<>|]', '_', filename)
    
def get_stem_pathlib(path: str) -> str:
    return sanitize_filename(Path(path).stem)

dirname = "file_search/" + get_stem_pathlib(args.pdf)
os.makedirs(dirname, exist_ok=True)

# ─── OpenAI client ────────────────────────────────────────────────────────────
from dotenv import load_dotenv  # Ensure you have python-dotenv installed
load_dotenv()  # Load environment variables from .env file
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise EnvironmentError("OPENAI_API_KEY env var not set.")
client = OpenAI(api_key=API_KEY)
POLL_SECS = 2

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_definitions(path: str) -> "OrderedDict[str, List[Dict]]":
    groups: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            groups[row["Label"].strip()].append(
                {
                    "column": row["Column Name"].strip(),
                    "definition": row["Definition"].strip(),
                }
            )
    return OrderedDict(groups)  # preserves CSV order


def build_prompt(label: str, items: List[Dict[str, str]]) -> str:
    lines = [f"ITEMS (Label = {label})"]
    for i, itm in enumerate(items, 1):
        lines.append(
            f"{i}. Find the value of {itm['column']}: {itm['definition']} from the PDF. "
            f"If it is not present, return \"not found\"."
        )
    return "\n".join(lines)

# ──────────────────────────────────────────────────────────────────────────────
#  Phase 1 – Extraction
# ──────────────────────────────────────────────────────────────────────────────
print("📑 Phase 1 – Extraction")
label_groups = load_definitions(args.defs)
if not label_groups:
    raise ValueError("Definitions.csv appears empty or malformed.")

max_workers = min(args.workers, len(label_groups)) or 1

print("📤 Uploading PDF …", end=" ")
with open(args.pdf, "rb") as f_pdf:
    pdf_file = client.files.create(file=f_pdf, purpose="assistants")
print(pdf_file.id)

print("🤖 Creating assistant …", end=" ")
assistant = client.beta.assistants.create(
    name="PDF Extractor (raw mode)",
    instructions=(
        """"You are provided with an input that includes one or more column definitions and the corresponding column names for which you need to extract values, along with a text chunk from a clinical trial document. Your task is to extract/infer the required value for each column from the text chunk by following these steps:

            1. **Interpret the Column Definition:**  
            Read the provided definition for the column and note any keywords, synonyms, or specific instructions. For example, if the definition mentions “synchronous metastases” and includes synonyms like “concurrent metastases” or “metastases at the time of diagnosis,” use those to guide your search.

            2. **Locate the Relevant Data:**  
            Search the provided text chunk for the presence of these keywords and phrases. Identify sentences, phrases, or numbers that match the definition of the column.  
            - For numeric values, extract the number exactly as it appears.  
            - For non-numeric values, if multiple expressions are possible, choose the one that best matches the meaning.

            3. **Handling Missing Data:**  
            If the required information is not present in the text chunk or cannot be unambiguously determined, mark its value as “not present.”

            5. **Compile the Answer:**  
            Once you have extracted the value for each column, compile your results into a JSON object.  
            The final answer must follow this exact output format:

            6. **Maintain Context**:
            Ensure that the extracted values are relevant to the context of the clinical trial document and adhere to the definitions provided. Make sure to avoid extracting values from other trials.

            
            ### REASONING STEPS
            [Provide a step-by-step explanation of how you extracted the value for each column, mentioning any keywords found, challenges encountered, and how you handled missing data.]

            ### FINAL ANSWER
            {
            "Column Name 1": "Extracted Value 1",
            "Column Name 2": "Extracted Value 2",
            ...
            }
             Return your output following the format specified above for the given columns and their definitions.""" 
    ),
    model=args.model,
    tools=[{"type": "file_search"}],
)
print(assistant.id)

# Token counters for phase 1
lock = threading.Lock()
phase1_in = 0
phase1_out = 0
raw_replies: OrderedDict[str, str] = OrderedDict()


def process_label(label: str, items: List[Dict[str, str]]) -> Tuple[str, str, int, int]:
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": build_prompt(label, items),
                "attachments": [
                    {"file_id": pdf_file.id, "tools": [{"type": "file_search"}]},
                ],
            }
        ]
    )
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run.status == "completed":
            break
        if run.status in {"failed", "cancelled", "expired"}:
            raise RuntimeError(f"Run failed (label={label}, status={run.status})")
        time.sleep(POLL_SECS)

    usage = run.usage
    in_toks = getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", 0)) if usage else 0
    out_toks = getattr(usage, "completion_tokens", getattr(usage, "output_tokens", 0)) if usage else 0

    msgs = client.beta.threads.messages.list(thread_id=thread.id)
    assistant_msg = next((m for m in msgs.data if m.role == "assistant"), None)
    if not assistant_msg:
        raise RuntimeError(f"No assistant reply for label {label}")

    return label, assistant_msg.content[0].text.value.strip(), in_toks, out_toks

print(f"🚀 Processing {len(label_groups)} labels with {max_workers} workers …")
with ThreadPoolExecutor(max_workers=max_workers) as exe:
    futures = {exe.submit(process_label, lbl, items): lbl for lbl, items in label_groups.items()}
    for fut in as_completed(futures):
        lbl = futures[fut]
        try:
            l, reply, in_tok, out_tok = fut.result()
            raw_replies[l] = reply
            with lock:
                phase1_in += in_tok
                phase1_out += out_tok
            print(f"✅ {l} (in={in_tok}, out={out_tok})")
        except Exception as exc:
            raw_replies[lbl] = f"ERROR: {exc}"
            print(f"❌ {lbl}: {exc}")

print(f"💾 Saving raw JSON → {dirname}/raw_outputs.json")
with open(f"{dirname}/raw_outputs.json", "w", encoding="utf-8") as jf:
    json.dump(raw_replies, jf, ensure_ascii=False, indent=2)

# ──────────────────────────────────────────────────────────────────────────────
#  Phase 2 – Post‑processing
# ──────────────────────────────────────────────────────────────────────────────
print("\n🧹 Phase 2 – Post‑processing")
json_str = json.dumps(raw_replies, ensure_ascii=False, indent=2)
post_prompt = f""" You are a post‑processing agent. You are given a JSON object where each key represents a column name and its value contains the value of the answer and a \"Final Answer\" section in a code block. Your task is to extract only the column names and their corresponding final answer values.\n\nFor each key in the JSON:\n1. Identify the \"Final Answer\" code block.\n2. Extract the value inside that code block.\n3. Output a clean entry in the format:\n   Column Name :: Final Answer Value\n\nReturn your final output as plain text with one entry per line. Use this illustration as a guiding template. Trial Name :: ENZAMET
Author :: Christopher J Sweeney, Andrew J Martin, Martin R Stockler, Stephen Begbie, Leanna Cheung, Kim N Chi, Simon Chowdhury, Mark Frydenberg, Lisa G Horvath, Anthony M Joshua, Nicola J Lawrence, Gavin Marx, John McCaffrey, Ray McDermott, Margaret McJannett, Scott A North, Francis Parnis, Wendy Parulekar, David W Pook, Martin Neil Reaume, Shahneen K Sandhu, Alvin Tan, Thean Hsiang Tan, Alastair Thomson, Francisco Vera-Badillo, Scott G Williams, Diana Winter, Sonia Yip, Alison Y Zhang, Robert R Zielinski, Ian D Davis
Year :: 2023
Full Pub or Abstract :: Full Pub
Phase :: III
Original/Follow Up :: Follow Up
Number of Arms Included :: 2
Treatment Arm(s) :: enzalutamide, standard non-steroidal antiandrogen
Control Arm :: Standard non-steroidal antiandrogen therapy
Class of Agent in Treatment Arm 1 :: Androgen Receptor Inhibitor
Treatment Arm 1 Regimen :: Enzalutamide (160 mg once per day)
Total Participants - N :: 1125
Treatment Arm - N :: 563
Control Arm - N :: 562
Median Follow-Up Duration (mo) :: 68
Median On-Treatment Duration (mo) | Treatment :: 58
Median On-Treatment Duration (mo) | Control :: 23

\n\nHere is the JSON:\njson\n{indent(json_str, '    ')}\n\n"""

post_thread = client.beta.threads.create(messages=[{"role": "user", "content": post_prompt}])
post_run = client.beta.threads.runs.create(thread_id=post_thread.id, assistant_id=assistant.id)
while True:
    post_run = client.beta.threads.runs.retrieve(thread_id=post_thread.id, run_id=post_run.id)
    if post_run.status == "completed":
        break
    if post_run.status in {"failed", "cancelled", "expired"}:
        raise RuntimeError(f"Post‑processing failed (status={post_run.status})")
    time.sleep(POLL_SECS)

usage2 = post_run.usage
phase2_in = getattr(usage2, "prompt_tokens", getattr(usage2, "input_tokens", 0)) if usage2 else 0
phase2_out = getattr(usage2, "completion_tokens", getattr(usage2, "output_tokens", 0)) if usage2 else 0

msgs2 = client.beta.threads.messages.list(thread_id=post_thread.id)
post_reply = next((m.content[0].text.value for m in msgs2.data if m.role == "assistant"), "")

print(f"💾 Saving processed TXT → {dirname}/pp_output.txt")
with open(f"{dirname}/pp_output.txt", "w", encoding="utf-8") as tf:
    tf.write(post_reply.strip() + "\n")

# ─── Cost summary ───────────────────────────────────────────────────────────
print("🔢 Token usage:")
print(f"   Phase 1 – input : {phase1_in}")
print(f"   Phase 1 – output: {phase1_out}")
print(f"   Phase 2 – input : {phase2_in}")
print(f"   Phase 2 – output: {phase2_out}")

total_in = phase1_in + phase2_in
total_out = phase1_out + phase2_out

print("💰 Estimated cost (GPT‑4o):")
print(f"   Input  cost: ${(total_in / 1000) * GPT4O_INPUT_PRICE:.4f}")
print(f"   Output cost: ${(total_out / 1000) * GPT4O_OUTPUT_PRICE:.4f}")
print(f"   Total  cost: ${((total_in / 1000) * GPT4O_INPUT_PRICE) + ((total_out / 1000) * GPT4O_OUTPUT_PRICE):.4f}")

print("✅ Pipeline complete.")