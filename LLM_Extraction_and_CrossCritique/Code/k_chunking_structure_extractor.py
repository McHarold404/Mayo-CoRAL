# structure_extractor.py
# -------------------------------------------------------------
# Adds "section" tags to chunks without touching downstream code.
# -------------------------------------------------------------
from __future__ import annotations
from pathlib import Path
import json, re, fitz, os, argparse
from typing import List, Dict, Any
from model_inference.gpt import ask_chatgpt_with_pdf
from model_inference.gemini import ask_gemini_with_image

# -- local utility already in your repo
from utils import get_model_function


# # ---------- 1) LLM-driven outline ---------------------------------
# PROMPT_PATH = "prompts/section_outline.txt"

# def _read_pdf_head(pdf_path: str, max_chars: int = 15000) -> str:
#     """Concatenate pages until max_chars; keeps prompt small."""
#     doc = fitz.open(pdf_path)
#     out = []
#     for page in doc:
#         out.append(page.get_text())
#         if sum(len(t) for t in out) > max_chars:
#             break
#     doc.close()
#     return "\n".join(out)[:max_chars]

# # def extract_document_structure(pdf_path: str,
# #                                config: Dict[str, Any]) -> List[Dict]:
# #     """Return [{title,start,end}, …] via ask_chatgpt."""
# #     user_text = _read_pdf_head(pdf_path)

# #     user_msg = (
# #         "Detect  major IMRaD-style sections ithen the text from the clinical trial below "
# #         "and respond ONLY with the specified JSON array.\n\nTEXT:\n"
# #         f"\"\"\"{user_text}\"\"\""
# #     )
# #     model_fn = get_model_function(config["model"]["type"])
# #     raw = model_fn(text=user_msg,
# #                    prompt_path=PROMPT_PATH,
# #                    key=config["model"]["key"])

# #     try:
# #         return json.loads(raw)
# #     except Exception:
# #         print("[WARN] could not parse section map; fallback = []")
# #         return []

# def extract_document_structure_2(pdf_path: str,
#                                config: Dict[str, Any]) -> List[Dict]:
#     """Return [{title,start,end}, …] via ask_chatgpt."""

#     with open(config["prompts"]["section_outline_prompt"], "r", encoding="utf-8") as f:
#         prompt = f.read()
#     raw = ask_chatgpt_with_pdf(pdf_path=pdf_path,prompt=prompt,poll=2)
#     # model_fn = get_model_function(config["model"]["type"])
#     # raw = model_fn(text=user_msg,
#     #                prompt_path=PROMPT_PATH,
#     #                key=config["model"]["key"])
#     print(f"[INFO] Raw section map: {raw[:1000]}...")  # Debugging output
#     try:
#         return json.loads(raw)
#     except Exception:
#         print("[WARN] could not parse section map; fallback = []")
#         return raw



# def tag_chunks_with_sections(chunks: List[Dict],
#                              section_map: List[Dict],
#                              full_text: str) -> List[Dict]:
#     """Add chunk['section'] field."""
#     spans = []
#     for sec in section_map:
#         s_pat = re.escape(sec["start"][:60])
#         e_pat = re.escape(sec["end"][-60:])
#         s_idx = full_text.find(s_pat)
#         e_idx = full_text.find(e_pat) + len(sec["end"])
#         if s_idx != -1 and e_idx != -1:
#             spans.append((s_idx, e_idx, sec["title"]))

#     def locate(snippet: str) -> str:
#         idx = full_text.find(snippet[:60])
#         for s, e, title in spans:
#             if s <= idx <= e:
#                 return title
#         return "Unknown"

#     for c in chunks:
#         if c["type"] in ("text", "image"):
#             c["section"] = locate(c["content"])
#         elif c["type"] == "table":
#             c["section"] = "Table"
#         elif c["type"] == "figure":
#             c["section"] = "Figure"
#         else:
#             c["section"] = "Unknown"
#     return chunks
import json
from io import BytesIO
from typing import List, Dict

import fitz                       # PyMuPDF
from PIL import Image
from rapidfuzz import fuzz        # optional: fuzzy-match utilities

def parse_gemini_response(raw: str, page_idx: int) -> List[Dict]:
    """
    Parse the custom format response from Gemini API.
    Expected format for each heading or subheading:
    ### Heading: <Heading Name>
    First 5 Words: <first 5 words or empty if not found>
    or
    ### Subheading: <Subheading Name>
    First 5 Words: <first 5 words or empty if not found>
    
    Returns a list of dictionaries with heading/subheading, first 5 words, and page number.
    """
    try:
        results = []
        lines = raw.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("### Heading: ") or line.startswith("### Subheading: "):
                heading_type, heading_name = line.split(":", 1)
                heading_name = heading_name.strip()
                if i + 1 < len(lines) and lines[i + 1].startswith("First 5 Words: "):
                    first5 = lines[i + 1].replace("First 5 Words: ", "").strip()
                    if first5:  # Only add if first 5 words are found
                        results.append({
                            "heading": heading_name,
                            "top_words": first5,
                            "page": page_idx,
                            "is_subheading": "Subheading" in heading_type
                        })
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        return results
    except Exception as err:
        print(f"[WARN] p{page_idx}: could not parse Gemini response format → {err}")
        return []

def extract_hierarchical_structure(pdf_path: str, prompt: str, output_dir: str, pdf_name: str, api_key: str = None) -> List[Dict]:
    """
    Extract the hierarchical structure of the PDF using ChatGPT with file-search tool.
    
    Parameters
    ----------
    pdf_path : str
        Path to the PDF.
    prompt : str
        Prompt to instruct ChatGPT on extracting hierarchical structure.
    output_dir : str
        Directory to store raw response.
    pdf_name : str
        Name of the PDF file for naming output files.
    api_key : str, optional
        Optional API key for ChatGPT. If not provided, uses environment variable.
    
    Returns
    -------
    List[Dict]
        Hierarchical structure of headings in the format of nested dictionaries or list.
    """
    try:
        raw = ask_chatgpt_with_pdf(pdf_path=pdf_path, prompt=prompt, api_key=api_key)
        print(f"[INFO] Raw hierarchical structure response: {raw[:500]}...")  # Debugging output
        
        # Save raw response
        raw_output_path = os.path.join(output_dir, pdf_name, f"{pdf_name}_gpt_structure_raw.txt")
        os.makedirs(os.path.dirname(raw_output_path), exist_ok=True)
        with open(raw_output_path, "w", encoding="utf-8") as f:
            f.write(raw)
        print(f"Raw hierarchical structure response saved to {raw_output_path}")
        
        try:
            return json.loads(raw)
        except Exception as err:
            print(f"[WARN] Could not parse hierarchical structure JSON → {err}")
            return []
    except Exception as err:
        print(f"[ERROR] Failed to extract hierarchical structure → {err}")
        return []

def map_page_data_to_structure(page_data: List[Dict], structure: List[Dict]) -> List[Dict]:
    """
    Map page-by-page extracted data to the hierarchical structure.
    
    Parameters
    ----------
    page_data : List[Dict]
        List of dictionaries with page-by-page extracted headings and first 5 words.
    structure : List[Dict]
        Hierarchical structure of the document.
    
    Returns
    -------
    List[Dict]
        Updated structure with first 5 words and page numbers integrated.
    """
    # Create a lookup dictionary for structure headings
    structure_lookup = {}
    def build_lookup(entries, parent_path=""):
        for entry in entries:
            title = entry.get("title", "")
            path = f"{parent_path}/{title}" if parent_path else title
            structure_lookup[path] = entry
            if "subheadings" in entry:
                build_lookup(entry["subheadings"], path)
    
    build_lookup(structure)
    
    # Map page data to structure
    for data in page_data:
        heading = data.get("heading", "")
        for path, entry in structure_lookup.items():
            if heading.lower() in path.lower():
                entry["top_words"] = data.get("top_words", "")
                entry["page"] = data.get("page", 0)
                break
    
    return structure

def extract_section_outline(
    pdf_path: str,
    prompt_template: str,
    model_key: str,
    output_dir: str,
    pdf_name: str,
    similarity_cutoff: int = 90,
    hierarchical_structure: List[Dict] = None
) -> List[Dict]:
    """
    Build outline with one record per section heading with its first 5 words.

    Each record shape:
        {
            "heading": "Patients and Methods",
            "top_words": "Patients and methods were prospectively",
            "page": 3
        }

    Parameters
    ----------
    pdf_path : str
        Path to the PDF.
    prompt_template : str
        Path to the prompt file sent to Gemini Vision.  
        It should instruct the model to return data in a custom format.
    model_key : str
        Gemini API key identifier (1-6).
    output_dir : str
        Directory to store the output JSON files.
    pdf_name : str
        Name of the PDF file for naming output files.
    similarity_cutoff : int, optional
        Deduplication threshold (RapidFuzz ratio). 90 ≈ “almost identical”.
    hierarchical_structure : List[Dict], optional
        Hierarchical structure of the document to guide extraction (if provided).

    Returns
    -------
    List[Dict]
        Parsed outline (also written to output files).
    """
    outline: List[Dict] = []
    raw_responses = []

    # Prepare user prompt text from hierarchical structure if provided
    user_prompt_text = ""
    if hierarchical_structure:
        # Read the raw GPT output file if it exists
        raw_output_path = os.path.join(output_dir, pdf_name, f"{pdf_name}_gpt_structure_raw.txt")
        if os.path.exists(raw_output_path):
            with open(raw_output_path, "r", encoding="utf-8") as f:
                user_prompt_text = f.read()
            print(f"[INFO] Raw GPT output loaded into user prompt text for Gemini from {raw_output_path}.")
        else:
            headings_text = []
            for entry in hierarchical_structure:
                title = entry.get("title", "")
                if title and title not in headings_text:
                    headings_text.append(title)
                if "subheadings" in entry:
                    for sub in entry.get("subheadings", []):
                        sub_title = sub.get("title", "")
                        if sub_title and sub_title not in headings_text:
                            headings_text.append(sub_title)
            user_prompt_text = "\n".join(headings_text)
            print(f"[INFO] User prompt text with headings prepared for Gemini (fallback to extracted headings).")

    doc = fitz.open(pdf_path)
    for page_idx, page in enumerate(doc.pages(), start=1):
        # ── 1️⃣  render page → image ────────────────────────────────────────────
        pix = page.get_pixmap()
        img_pil = Image.open(BytesIO(pix.tobytes("png")))

        # ── 2️⃣  query Gemini Vision ───────────────────────────────────────────
        raw = ask_gemini_with_image(
            img_pil,
            prompt_template,
            user_prompt_text=user_prompt_text,
        )

        # Store raw response
        raw_responses.append({
            "page": page_idx,
            "raw_response": raw
        })

        # expected format:
        # ### Heading: <Heading Name>
        # First 5 Words: <first 5 words or empty if not found>
        print(f"[DEBUG] p{page_idx}: Raw Gemini response: {raw}")
        page_results = parse_gemini_response(raw, page_idx)

        if page_results:
            outline.extend(page_results)

    # ── 3️⃣  persist to disk ───────────────────────────────────────────────────
    output_path = os.path.join(output_dir, pdf_name, f"{pdf_name}_outline.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(outline, f, indent=2, ensure_ascii=False)
    print(f"Section outline saved to {output_path}")

    # Save raw responses
    raw_responses_path = os.path.join(output_dir, pdf_name, f"{pdf_name}_gemini_raw_responses.json")
    with open(raw_responses_path, "w", encoding="utf-8") as f:
        json.dump(raw_responses, f, indent=2, ensure_ascii=False)
    print(f"Raw Gemini responses saved to {raw_responses_path}")

    # If hierarchical structure is provided, map the page data to it
    if hierarchical_structure:
        final_outline = map_page_data_to_structure(outline, hierarchical_structure)
        hierarchical_output_path = os.path.join(output_dir, pdf_name, f"{pdf_name}_outline_hierarchical.json")
        with open(hierarchical_output_path, "w", encoding="utf-8") as f:
            json.dump(final_outline, f, indent=2, ensure_ascii=False)
        print(f"Hierarchical outline saved to {hierarchical_output_path}")
        return final_outline

    return outline

def main():
    parser = argparse.ArgumentParser(description="Extract section outline from a PDF using Gemini Vision API.")
    parser.add_argument("--pdf", type=str, default="training_studies/NCT00104715_Gravis_GETUG_Lancet Onc'13.pdf", help="Path to the PDF file.")
    parser.add_argument("--prompt", type=str, default="prompts/section_top_words.txt", help="Path to the prompt file for Gemini Vision.")
    parser.add_argument("--structure-prompt", type=str, default="prompts/hierarchical_structure.txt", help="Path to the prompt file for hierarchical structure extraction.")
    parser.add_argument("--key", type=str, default="2", help="Gemini API key identifier (1-6).")
    parser.add_argument("--output-dir", type=str, default="db", help="Base directory to store the output JSON files.")
    args = parser.parse_args()

    # Ensure base output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Derive output subdirectory from PDF name
    pdf_name = os.path.basename(args.pdf).replace(".pdf", "")
    output_subdir = os.path.join(args.output_dir, pdf_name)
    os.makedirs(output_subdir, exist_ok=True)
    
    # Read prompt templates
    with open(args.prompt, "r", encoding="utf-8") as f:
        prompt_template = f.read()
    
    print(f"Extracting hierarchical structure from {args.pdf}...")
    with open(args.structure_prompt, "r", encoding="utf-8") as f:
        structure_prompt = f.read()
    hierarchical_structure = extract_hierarchical_structure(
        pdf_path=args.pdf,
        prompt=structure_prompt,
        output_dir=args.output_dir,
        pdf_name=pdf_name
    )
    structure_output_path = os.path.join(output_subdir, f"{pdf_name}_structure.json")
    with open(structure_output_path, "w", encoding="utf-8") as f:
        json.dump(hierarchical_structure, f, indent=2, ensure_ascii=False)
    print(f"Hierarchical structure saved to {structure_output_path}")
    
    print(f"Extracting section outline from {args.pdf}...")
    outline = extract_section_outline(
        pdf_path=args.pdf,
        prompt_template=args.prompt,
        model_key=args.key,
        output_dir=args.output_dir,
        pdf_name=pdf_name,
        hierarchical_structure=hierarchical_structure
    )
    print("Extracted sections:")
    for section in outline:
        print(f"- {section.get('title', section.get('heading', 'Unknown'))} (Page {section.get('page', 'N/A')}): {section.get('top_words', 'N/A')}")

if __name__ == "__main__":
    main()
