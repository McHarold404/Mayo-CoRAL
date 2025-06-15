# structure_extractor.py
# -------------------------------------------------------------
# Adds "section" tags to chunks without touching downstream code.
# -------------------------------------------------------------
from __future__ import annotations
from pathlib import Path
import json, re, fitz
from typing import List, Dict, Any

# -- local utility already in your repo
from utils import get_model_function


# ---------- 1) LLM-driven outline ---------------------------------
PROMPT_PATH = "prompts/section_outline.txt"

def _read_pdf_head(pdf_path: str, max_chars: int = 15000) -> str:
    """Concatenate pages until max_chars; keeps prompt small."""
    doc = fitz.open(pdf_path)
    out = []
    for page in doc:
        out.append(page.get_text())
        if sum(len(t) for t in out) > max_chars:
            break
    doc.close()
    return "\n".join(out)[:max_chars]

def extract_document_structure(pdf_path: str,
                               config: Dict[str, Any]) -> List[Dict]:
    """Return [{title,start,end}, …] via ask_chatgpt."""
    user_text = _read_pdf_head(pdf_path)

    user_msg = (
        "Detect the major IMRaD-style sections in the text below "
        "and respond ONLY with the specified JSON array.\n\nTEXT:\n"
        f"\"\"\"{user_text}\"\"\""
    )

    model_fn = get_model_function(config["model"]["type"])
    raw = model_fn(text=user_msg,
                   prompt_path=PROMPT_PATH,
                   key=config["model"]["key"])

    try:
        return json.loads(raw)
    except Exception:
        print("[WARN] could not parse section map; fallback = []")
        return []

def tag_chunks_with_sections(chunks: List[Dict],
                             section_map: List[Dict],
                             full_text: str) -> List[Dict]:
    """Add chunk['section'] field."""
    spans = []
    for sec in section_map:
        s_pat = re.escape(sec["start"][:60])
        e_pat = re.escape(sec["end"][-60:])
        s_idx = full_text.find(s_pat)
        e_idx = full_text.find(e_pat) + len(sec["end"])
        if s_idx != -1 and e_idx != -1:
            spans.append((s_idx, e_idx, sec["title"]))

    def locate(snippet: str) -> str:
        idx = full_text.find(snippet[:60])
        for s, e, title in spans:
            if s <= idx <= e:
                return title
        return "Unknown"

    for c in chunks:
        if c["type"] in ("text", "image"):
            c["section"] = locate(c["content"])
        elif c["type"] == "table":
            c["section"] = "Table"
        elif c["type"] == "figure":
            c["section"] = "Figure"
        else:
            c["section"] = "Unknown"
    return chunks
