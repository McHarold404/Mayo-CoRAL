import os
import re
import json
import base64
import argparse
import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
from io import BytesIO
from PIL import Image
from langchain.text_splitter import RecursiveCharacterTextSplitter
from model_inference.gemini import ask_gemini_with_image
from utils import extract_caption

# Define the splitter for text chunking
SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=3000,          # chars per chunk
    chunk_overlap=150,        # chars of overlap
    separators=["\n\n", "\n", " ", ""],   # try paragraph → line → word → char
)

def looks_like_inline_table(text: str) -> bool:
    lines = text.split("\n")
    if len(lines) < 3:
        return False
    digit_lines = sum(
        1 for ln in lines if re.search(r"\d", ln) and re.search(r"\(.+\)", ln)
    )
    return digit_lines / len(lines) > 0.5

def is_caption_or_footnote(text: str) -> bool:
    return bool(
        re.search(r"^\s*(Table|Fig|Figure)\s+\d+", text, re.IGNORECASE)
        or "TD$FIG" in text
        or re.search(r"\b[A-Z]{2,}\s*=", text)
    )

def extract_tables_for_page(page_plumber) -> list[str]:
    try:
        tables = page_plumber.extract_tables()
        out = []
        for tbl in tables:
            df = pd.DataFrame(tbl)
            header = df.iloc[0].tolist() if df.shape[0] > 1 else None
            df = df[1:].reset_index(drop=True) if header else df
            md = (
                df.to_markdown(index=False, headers=header)
                if header
                else df.to_markdown(index=False)
            )
            out.append(md.strip())
        return out
    except Exception:
        return []

def extract_images_for_page(page: fitz.Page, page_num: int) -> list[dict]:
    imgs = []
    for img in page.get_images(full=True):
        xref = img[0]
        img_bytes = page.parent.extract_image(xref)["image"]
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        imgs.append(
            {
                "type": "image",
                "content": f"Image of size {len(img_b64)} characters (Base64)",
                "page": page_num,
                "length": len(img_b64),
            }
        )
    return imgs

def chunk_pdf_recursive(pdf_path: str) -> list[dict]:
    chunks = []
    pdf_doc = fitz.open(pdf_path)
    plumber_doc = pdfplumber.open(pdf_path)

    stop_at_refs = False  # stop flag once 'References' detected

    for idx in range(len(pdf_doc)):
        if stop_at_refs:
            break

        page_fitz = pdf_doc[idx]
        page_num = idx + 1
        raw_text = page_fitz.get_text("text")

        # Cut off References/Bibliography onwards
        match = re.search(r"(?i)\b(references|bibliography)\b", raw_text)
        if match:
            stop_at_refs = True
            raw_text = raw_text[: match.start()].strip()

        # --- TEXT -------------------------------------------------------------
        if raw_text.strip():
            # remove obvious inline tables / captions before splitting
            clean_lines = []
            for ln in raw_text.splitlines():
                if looks_like_inline_table(ln) or is_caption_or_footnote(ln):
                    continue
                clean_lines.append(ln)
            cleaned_text = "\n".join(clean_lines)

            for slice_txt in SPLITTER.split_text(cleaned_text):
                chunks.append(
                    {
                        "type": "text",
                        "content": slice_txt,
                        "page": page_num,
                        "length": len(slice_txt),
                    }
                )

        # --- TABLES -----------------------------------------------------------
        for md_table in extract_tables_for_page(plumber_doc.pages[idx]):
            chunks.append(
                {
                    "type": "table",
                    "content": md_table,
                    "page": page_num,
                    "length": len(md_table),
                    "source": "pdfplumber",
                }
            )

        # --- IMAGES / FIGURES -------------------------------------------------
        chunks.extend(extract_images_for_page(page_fitz, page_num))

        # OPTIONAL: render full-page snapshot for pages containing “Table n” / “Fig n”
        keywords = {
            "table": re.search(r"\btable[s]?[ .:-]*\d+", raw_text, re.IGNORECASE),
            "figure": re.search(r"\bfig(?:ure)?s?[ .:-]*\d+", raw_text, re.IGNORECASE),
        }
        for vtype, m in keywords.items():
            if m:
                pix = page_fitz.get_pixmap(matrix=fitz.Matrix(4, 4))
                img_b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
                chunks.append(
                    {
                        "type": vtype,
                        "content": f"Image of size {len(img_b64)} characters (Base64)",
                        "page": page_num,
                        "length": len(img_b64),
                        "source": "image",
                    }
                )

    pdf_doc.close()
    plumber_doc.close()
    return chunks

def save_chunks(chunks: list[dict], out_path: str) -> None:
    # Ensure the directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(chunks, fp, ensure_ascii=False, indent=4)
    print(f"✓ Saved {len(chunks)} chunks → {out_path}")

def enrich_table_chunks(chunks, pdf_path, prompt_paths, config):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF file: {e}")
        return chunks

    for chunk in chunks:
        chunk_type = chunk.get("type")
        if chunk_type in ["table", "figure"]:
            page_num = chunk.get("page")
            if page_num is None:
                continue
            try:
                page = doc[page_num - 1]
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")
                img_pil = Image.open(BytesIO(img_bytes))

                # Use the prompt_path passed in
                gemini_output = ask_gemini_with_image(img_pil, prompt_paths[f'{chunk_type}'], key=config["model"]["key"])
                print(prompt_paths[f'{chunk_type}'], gemini_output)
                # Save under a common key since it may be table or figure
                chunk[f"{chunk_type}_content"] = gemini_output
                if chunk_type == "table":
                    chunk["content"] = extract_caption(gemini_output)
                elif chunk_type == "figure":
                    chunk["content"] = gemini_output

            except Exception as e:
                print(f"Error processing {chunk['type']} chunk on page {page_num}: {e}")

    doc.close()
    return chunks

def determine_study_directory(pdf_path: str, study_id: str = None) -> str:
    """Determine the study directory based on PDF filename or provided study ID."""
    base_dir = "db"
    if study_id:
        study_dir = os.path.join(base_dir, study_id)
    else:
        # Extract study identifier from PDF filename
        filename = os.path.basename(pdf_path)
        study_id = filename.split('_')[0] if '_' in filename else filename.split('.')[0]
        study_dir = os.path.join(base_dir, study_id)
    return study_dir

def test_paths(args):
    """Test all paths used in the script to ensure they exist or are accessible."""
    print("Testing paths used in the script (assuming root directory is 'Code'):")
    
    # Test PDF path
    pdf_path = args.pdf
    if os.path.exists(pdf_path):
        print(f"✓ PDF path exists: {pdf_path}")
    else:
        print(f"✗ PDF path does not exist: {pdf_path}")
    
    # Test config path
    config_path = args.config
    if os.path.exists(config_path):
        print(f"✓ Config path exists: {config_path}")
    else:
        print(f"✗ Config path does not exist: {config_path}")
    
    # Test table prompt path
    table_prompt_path = args.table_prompt
    if os.path.exists(table_prompt_path):
        print(f"✓ Table prompt path exists: {table_prompt_path}")
    else:
        print(f"✗ Table prompt path does not exist: {table_prompt_path}")
    
    # Test figure prompt path
    figure_prompt_path = args.figure_prompt
    if os.path.exists(figure_prompt_path):
        print(f"✓ Figure prompt path exists: {figure_prompt_path}")
    else:
        print(f"✗ Figure prompt path does not exist: {figure_prompt_path}")
    
    # Test output directory
    study_dir = determine_study_directory(pdf_path, args.study)
    output_path = os.path.join(study_dir, args.out)
    output_dir = os.path.dirname(output_path)
    if os.path.exists(output_dir):
        print(f"✓ Output directory exists: {output_dir}")
    else:
        print(f"✓ Output directory will be created: {output_dir}")
    print("Path testing complete.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="PDF → JSON chunker with recursive text splitting")
    ap.add_argument("-pdf", default = "training_studies/NCT00309985_Kriayako_CHAARTED_JCO'18.pdf",help="Path to PDF file")
    ap.add_argument("-s", "--study", default=None, help="Study identifier for output directory (optional)")
    ap.add_argument("-o", "--out", default="hybrid_chunks.json", help="Output JSON filename (default: hybrid_chunks.json)")
    ap.add_argument("-c", "--config", default="config.json", help="Path to config JSON file for enrichment")
    ap.add_argument("-tp", "--table-prompt", default="prompts/extract_table.txt", help="Path to table prompt file for enrichment")
    ap.add_argument("-fp", "--figure-prompt", default="prompts/extract_figure.txt", help="Path to figure prompt file for enrichment")
    ap.add_argument("-t", "--test", action="store_true", help="Run a test on all paths to verify accessibility")
    args = ap.parse_args()

    # Determine the output directory based on study ID or PDF filename
    study_dir = determine_study_directory(args.pdf, args.study)
    output_path = os.path.join(study_dir, args.out)

    # Run path test if requested
    if args.test:
        test_paths(args)
        exit(0)

    # Check if output file already exists
    if os.path.exists(output_path):
        print(f"Warning: Output file {output_path} already exists. It will not be overwritten.")
        response = input("Do you want to overwrite the existing file? (y/n): ")
        if response.lower() != 'y':
            print("Processing aborted to avoid overwriting existing file.")
            exit(0)

    # Load configuration for enrichment
    config = {}
    try:
        with open(args.config, 'r') as config_file:
            config = json.load(config_file)
    except Exception as e:
        print(f"Error loading config file: {e}. Proceeding without enrichment.")

    # Define prompt paths for table and figure enrichment
    prompt_paths = {
        "table": args.table_prompt,
        "figure": args.figure_prompt
    }

    # Process the PDF
    data = chunk_pdf_recursive(args.pdf)
    
    # Enrich chunks if config is loaded successfully
    if config:
        data = enrich_table_chunks(data, args.pdf, prompt_paths, config)
    else:
        print("Skipping chunk enrichment due to missing or invalid config.")
    
    save_chunks(data, output_path)
