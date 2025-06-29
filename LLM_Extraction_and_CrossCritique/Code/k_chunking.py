import fitz  # PyMuPDF
import pdfplumber
import os
import json
import base64
import spacy
import pandas as pd
import re
from PIL import Image
from io import BytesIO
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from model_inference.gemini import *
from model_inference.gpt import *
from utils import extract_caption

# Load NLP model
nlp = spacy.load("en_core_web_sm")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# def semantic_text_chunking(text, min_size=1000):
#     doc = nlp(text)
#     chunks = []
#     current_chunk = ""

#     for sent in doc.sents:
#         if len(current_chunk) < min_size:
#             current_chunk += " " + sent.text.strip()
#         else:
#             chunks.append(current_chunk.strip())
#             current_chunk = sent.text.strip()

#     if current_chunk:
#         chunks.append(current_chunk.strip())

#     return chunks

def looks_like_inline_table(text):
    lines = text.split("\n")
    if len(lines) < 3:
        return False
    digit_lines = sum(1 for line in lines if re.search(r'\d', line) and re.search(r'\(.+\)', line))
    return digit_lines / len(lines) > 0.5

def is_table_caption_or_footnote(text):
    # Skip fig/table labels or metadata lines
    return bool(
        re.search(r'^\s*(Table|Fig|Figure)\s+\d+', text, re.IGNORECASE)
        or 'TD$FIG' in text
        or re.search(r'\b[A-Z]{2,}\s*=', text)  # e.g. ADT = ...
    )

def semantic_text_chunking(text, min_size=1000):
    doc = nlp(text)
    chunks = []
    current_chunk = ""

    for sent in doc.sents:
        sentence = sent.text.strip()

        # Skip sentences that look like tables or metadata
        if looks_like_inline_table(sentence) or is_table_caption_or_footnote(sentence):
            continue

        current_chunk += " " + sentence

        if len(current_chunk) >= min_size:
            chunks.append(current_chunk.strip())
            current_chunk = ""

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def extract_tables_for_page(page):
    try:
        tables = page.extract_tables()
        table_chunks = []
        for table in tables:
            df = pd.DataFrame(table)
            header = df.iloc[0].tolist() if df.shape[0] > 1 else None
            df = df[1:].reset_index(drop=True) if header else df
            markdown = df.to_markdown(index=False, headers=header) if header else df.to_markdown(index=False)
            table_chunks.append(markdown.strip())
        return table_chunks
    except:
        return []

def extract_images_for_page(page, page_num):
    images = page.get_images(full=True)
    img_chunks = []
    for img in images:
        xref = img[0]
        base_image = page.parent.extract_image(xref)
        image_bytes = base_image["image"]
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        img_chunks.append({
            "type": "image",
            "content": f"Image of size {len(image_base64)} characters (Base64)",
            "page": page_num,
            "length": len(image_base64)
        })
    return img_chunks

def chunking(pdf_path):
    chunks = []

    try:
        text_doc = fitz.open(pdf_path)
        stop_processing = False  # Flag to stop processing after finding "References"
        for page_num in range(len(text_doc)):
            if stop_processing:
                break  # ✅ Skip all pages after references

            page_chunks = []
            page = text_doc[page_num]
            raw_text = page.get_text("text")

            #  Detect the start of "References" section
            match = re.search(r'(?i)\b(references|bibliography)\b', raw_text)
            if match:
                stop_processing = True  # ✅ This is the last page we'll process
                # ✂ Cut off the page content from the reference section onwards
                raw_text = raw_text[:match.start()].strip()

            # Step 1: Text chunking
            if raw_text.strip():
                for chunk in semantic_text_chunking(raw_text):
                    page_chunks.append({
                        "type": "text",
                        "content": chunk,
                        "page": page_num + 1,
                        "length": len(chunk)
                    })

            # Step 2: Detect table (only if relevant keyword appears)
            # if any(keyword in raw_text for keyword in ["Table", "TABLE", "table"]):
            #     pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))  # High-res render
            #     img_bytes = pix.tobytes("png")
            #     image_base64 = base64.b64encode(img_bytes).decode("utf-8")

            #     page_chunks.append({
            #         "type": "table",
            #         "content": f"Image of size {len(image_base64)} characters (Base64)",
            #         "page": page_num + 1,
            #         "length": len(image_base64),
            #         "source": "image"
            #         # "image_base64": image_base64
            #     })

            keywords = {
                "table": re.search(r"\btable[s]?[ .:-]*\d+", raw_text, re.IGNORECASE),
                "figure": re.search(r"\bfig(?:ure)?s?[ .:-]*\d+", raw_text, re.IGNORECASE) ##uncomment this line if you want to use figures also
            }

            for visual_type, match in keywords.items():
                if match:
                    pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))  # High-res
                    img_bytes = pix.tobytes("png")
                    image_base64 = base64.b64encode(img_bytes).decode("utf-8")

                    page_chunks.append({
                        "type": visual_type,
                        "content": f"Image of size {len(image_base64)} characters (Base64)",
                        "page": page_num + 1,
                        "length": len(image_base64),
                        "source": "image"
                    })


            # Step 3: Extract images from the current page
            image_chunks = extract_images_for_page(page, page_num + 1)
            page_chunks.extend(image_chunks)

            chunks.extend(page_chunks)

        text_doc.close()

    except Exception as e:
        print(f"Chunking failed: {e}")

    return chunks


def save_chunks_to_json(chunks, output_path):
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(chunks, json_file, ensure_ascii=False, indent=4)
    print(f"Chunks saved to JSON file: {output_path}")

# def enrich_table_chunks(chunks, pdf_path, prompt_path, config):
#     try:
#         doc = fitz.open(pdf_path)
#     except Exception as e:
#         print(f"Error opening PDF file: {e}")
#         return chunks

#     for chunk in chunks:
#         if chunk.get("type") == "table":
#             page_num = chunk.get("page")
#             if page_num is None:
#                 continue
#             try:
#                 page = doc[page_num - 1]
#                 pix = page.get_pixmap()
#                 img_bytes = pix.tobytes("png")
#                 img_pil = Image.open(BytesIO(img_bytes))
#                 gemini_output = ask_gemini_with_image(img_pil, prompt_path, key=config["model"]["key"])
#                 chunk["table_content"] = gemini_output
#                 chunk["content"] = extract_caption(gemini_output)
#             except Exception as e:
#                 print(f"Error processing table chunk on page {page_num}: {e}")

#     doc.close()
#     return chunk

def enrich_table_chunks(chunks, pdf_path, prompt_paths, config):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF file: {e}")
        return chunks

    for chunk in chunks:
        chunk_type = chunk.get("type")
        if chunk_type in ["table","figure"]: #["table", "figure"]:  # ✅ change the line to do both table and figures, also change line 156.
            
            page_num = chunk.get("page")
            if page_num is None:
                continue
            try:
                page = doc[page_num - 1]
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")
                img_pil = Image.open(BytesIO(img_bytes))

                # ✅ Use the prompt_path passed in — don't override it!
                gemini_output = ask_gemini_with_image(img_pil, prompt_path=prompt_paths[f'{chunk_type}'], key=config["model"]["key"])
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




from PIL import Image
from io import BytesIO
import fitz  # PyMuPDF

def generate_context(pdf_path, prompt_path, config):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"❌ Error opening PDF file: {e}")
        return ""

    try:
        images = []
        for page_num in [1, 2]:
            page = doc[page_num - 1]
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            img_pil = Image.open(BytesIO(img_bytes)).convert("RGB")
            images.append(img_pil)

        # Send both images in one prompt
        summary = ask_gemini_with_image(images, prompt_path, key=config["model"]["key"])

    except Exception as e:
        print(f"❌ Error processing pages 1 and 2: {e}")
        summary = ""

    doc.close()
    return summary.strip()