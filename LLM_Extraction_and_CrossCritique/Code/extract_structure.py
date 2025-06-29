#!/usr/bin/env python3
"""
smart_sections_fixed.py
───────────────────────
LLM-assisted section extractor (final, fixed version)
"""

import argparse, json, re, sys
from pathlib import Path
from collections import OrderedDict

import fitz                   # PyMuPDF
import numpy as np
from openai import OpenAI
import os
from dotenv import load_dotenv

# ───── Load API Key ─────
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("❌ OPENAI_API_KEY not found. Make sure it's in your .env file.")

client = OpenAI(api_key=api_key)

# ───── Config ─────
MODEL_OUTLINE   = "gpt-4o"
FIRST_N_PAGES   = 3
SENT_SPLIT_RX   = re.compile(r"(?<=[.!?])\s+")
NUM_HEAD_RX     = re.compile(r"^\s*\d+(\.\d+)*\s+[A-Z]")
ALL_CAPS_RX     = re.compile(r"^[A-Z][A-Z \-]{3,}$")


# ───── Helpers ─────
def canon(text: str) -> str:
    text = re.sub(r"^\s*\d+(\.\d+)*\s*", "", text)
    return re.sub(r"\s+", " ", text.lower()).strip()

def sent_list(text, n=5):
    parts = [s.strip() for s in SENT_SPLIT_RX.split(text) if s.strip()]
    return parts[:n]

def looks_like_heading(line, big_font_threshold):
    txt   = line["text"].strip()
    words = txt.split()
    if len(words) > 12 or len(txt) < 10:
        return False
    if "," in txt and len(words) > 1:
        return False
    big      = line["size"] >= big_font_threshold
    numbered = bool(NUM_HEAD_RX.match(txt))
    allcaps  = bool(ALL_CAPS_RX.match(txt))
    bold_tc  = "Bold" in line["font"] and txt.istitle()
    return big or numbered or allcaps or bold_tc


# ───── Stage A: PDF → lines ─────
def extract_lines(pdf_path: Path):
    lines = []
    with fitz.open(pdf_path) as doc:
        for pno, page in enumerate(doc):
            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0 or "lines" not in block:
                    continue
                for ln in block["lines"]:
                    if not ln["spans"]:
                        continue
                    span = ln["spans"][0]
                    lines.append(
                        {
                            "page": pno,
                            "text": span["text"].rstrip(),
                            "size": span["size"],
                            "font": span["font"],
                        }
                    )
    return lines


# ───── Stage B: GPT outline ─────
def ask_outline(lines, max_pages):
    front = "\n".join(ln["text"] for ln in lines if ln["page"] < max_pages)
    # prompt = (
    #     "You will receive a research paper. "
    #     "Return ONLY valid JSON of the form {\"sections\":[\"…\", …]} "
    #     "with the MAJOR top-level headings exactly as written and in order. "
    #     "Do NOT invent headings and do NOT output anything except the JSON. no extra prose, markdown, or code fences."
    # )
    prompt = (
        "You will receive the first pages of a research paper.\n"
        "Return ONLY valid JSON of the form:\n"
        "{\n"
        "  \"sections\": [\n"
        "    \"<Heading>: <first 5 words of that section>\",\n"
        "    …\n"
        "  ]\n"
        "}\n"
        "List each top-level heading prefixed with `<Heading>: ` followed by the first five words "
        "of that section, in their order of appearance. "
        "Do NOT invent headings and do NOT output anything except the JSON. No extra prose, markdown, or code fences."
    )
    rsp = client.chat.completions.create(
        model=MODEL_OUTLINE,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": front}
        ],
        temperature=0,
    )
    content = rsp.choices[0].message.content.strip()
    if not content.startswith("{"):
        print("‼️ GPT returned non-JSON response:\n", content[:300])
        return []
    try:
        return json.loads(content)["sections"]
    except Exception as e:
        print("‼️ GPT outline parse error:", e)
        print("↪ raw content:\n", content[:300])
        return []


# ───── Stage C: candidate headings ─────
def heading_candidates(lines, big_font_threshold):
    cand = []
    for idx, ln in enumerate(lines):
        if looks_like_heading(ln, big_font_threshold):
            cand.append((idx, ln["text"].strip()))
    merged = []
    for idx, txt in cand:
        if merged and idx == merged[-1][0] + 1:
            merged[-1][1] += " " + txt
        else:
            merged.append([idx, txt])
    return [(i, canon(t)) for i, t in merged]


# ───── Stage D: match LLM titles to PDF ─────
def verify_anchors(candidates, llm_titles):
    anchors, start_ptr = [], 0
    norm_titles = [canon(t) for t in llm_titles]
    for nt in norm_titles:
        for pos in range(start_ptr, len(candidates)):
            idx, cand_txt = candidates[pos]
            if cand_txt == nt:
                anchors.append((idx, llm_titles[norm_titles.index(nt)].strip()))
                start_ptr = pos + 1
                break
    return anchors


# ───── Stage E: tag all lines by section ─────
def propagate(lines, anchors, cand_indices):
    labels = ["Unknown"] * len(lines)
    cur = None
    hptr = 0
    for i in range(len(lines)):
        if hptr < len(anchors) and i == anchors[hptr][0]:
            cur = anchors[hptr][1]
            hptr += 1
        if i in cand_indices:
            continue
        labels[i] = cur
    return labels


# ───── Stage F: collect top 5 sentences ─────
def aggregate(lines, labels):
    sections = OrderedDict()
    for lab, ln in zip(labels, lines):
        if lab not in sections:
            sections[lab] = []
        sections[lab].append(ln["text"])
    out = []
    for sec, txts in sections.items():
        body = " ".join(txts)
        out.append({"section": sec, "sentences": sent_list(body)})
    return out


# ───── Top-level function ─────
def extract_sections(pdf_path: Path, first_pages: int):
    lines = extract_lines(pdf_path)
    sizes = np.array([l["size"] for l in lines])
    big_thresh = np.percentile(sizes, 90)

    llm_titles = ask_outline(lines, max_pages=first_pages)
    print("GPT titles:", llm_titles)

    cand = heading_candidates(lines, big_thresh)
    cand_idx = {i for i, _ in cand}

    anchors = verify_anchors(cand, llm_titles)
    print("Verified anchors:", anchors)

    labels = propagate(lines, anchors, cand_idx)
    return aggregate(lines, labels)


# ───── CLI ─────
def main():
    ap = argparse.ArgumentParser(description="LLM-assisted section extractor")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--pages", type=int, default=FIRST_N_PAGES)
    args = ap.parse_args()

    if not args.pdf.exists():
        sys.exit(f"PDF not found: {args.pdf}")

    payload = extract_sections(args.pdf, first_pages=args.pages)
    out_path = args.out or args.pdf.with_suffix("_sections.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"✓ wrote {out_path}")


if __name__ == "__main__":
    main()
