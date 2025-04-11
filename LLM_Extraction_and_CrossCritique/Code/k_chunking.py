# import fitz  # PyMuPDF for text and image extraction
# import pdfplumber  # Alternative table extraction
# import os
# import json
# import base64
# import spacy
# import pandas as pd
# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity
# from model_inference.gemini import *
# from model_inference.gpt import *
# from utils import extract_caption

# # Load NLP model for text segmentation
# nlp = spacy.load("en_core_web_sm")
# embedding_model = SentenceTransformer("all-MiniLM-L6-v2")  # Lightweight model for semantic merging

# def semantic_text_chunking(text, min_size=1000,merge_threshold=0.8):
#     """
#     Uses NLP to split text into semantic chunks and merges similar chunks based on embeddings.
#     """
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
    
#     embeddings = embedding_model.encode(chunks)
#     similarities = cosine_similarity(embeddings, embeddings)
    
#     merged_chunks = []
#     visited = set()
    
#     for i, chunk in enumerate(chunks):
#         if i in visited:
#             continue
#         similar = [chunk]

#         for j in range(i+1, len(chunks)):
#             if similarities[i][j] > merge_threshold:
#                 similar.append(chunks[j])
#                 visited.add(j)
        
#         merged_chunks.append(" ".join(similar))

#     return merged_chunks

# def extract_tables(pdf_path):
#     """
#     Extract tables using PDFPlumber and format them in Markdown.
#     """
#     extracted_tables = []
    
#     try:
#         with pdfplumber.open(pdf_path) as pdf:
#             for page_num, page in enumerate(pdf.pages, start=1):
#                 tables_on_page = page.extract_tables()
                
#                 if tables_on_page:
#                     combined_table = ""  # Store combined markdown tables
                    
#                     for table in tables_on_page:
#                         df = pd.DataFrame(table)
#                         header = df.iloc[0].tolist() if df.shape[0] > 1 else None
#                         df = df[1:].reset_index(drop=True) if header else df
#                         markdown_table = df.to_markdown(index=False, headers=header) if header else df.to_markdown(index=False)
#                         combined_table += "\n\n" + markdown_table
                    
#                     extracted_tables.append({
#                         "type": "table",
#                         "content": combined_table.strip(),
#                         "page": page_num,
#                         "length": len(combined_table)
#                     })
#     except Exception as e:
#         print(f"Error extracting tables: {e}")
    
#     return extracted_tables

# def extract_images(pdf_path):
#     """ Extracts images and encodes them in Base64. """
#     image_chunks = []
#     doc = fitz.open(pdf_path)
    
#     for page_num, page in enumerate(doc, start=1):
#         images = page.get_images(full=True)
#         for img_index, img in enumerate(images):
#             xref = img[0]
#             base_image = doc.extract_image(xref)
#             image_bytes = base_image["image"]
#             image_base64 = base64.b64encode(image_bytes).decode('utf-8')
#             image_chunks.append({
#                 "type": "image",
#                 "content": f"Image of size {len(image_base64)} characters (Base64)",
#                 "page": page_num,
#                 "length": len(image_base64)
#             })
    
#     return image_chunks

# def chunking(pdf_path):
#     """
#     Extract and segment the document into semantic text chunks, tables, and images.
#     """
#     chunks = []
    
#     # Extract text
#     try:
#         doc = fitz.open(pdf_path)
#         for page_num, page in enumerate(doc, start=1):
#             raw_text = page.get_text("text")
#             if raw_text.strip():
#                 text_chunks = semantic_text_chunking(raw_text,min_size=1000)
#                 for chunk in text_chunks:
#                     chunks.append({
#                         "type": "text",
#                         "content": chunk,
#                         "page": page_num,
#                         "length": len(chunk)
#                     })
#     except Exception as e:
#         print(f"Error extracting text: {e}")
    
#     # Extract tables
#     chunks.extend(extract_tables(pdf_path))
    
#     # Extract images
#     chunks.extend(extract_images(pdf_path))
    
#     return chunks

# def save_chunks_to_json(chunks, output_path):
#     """
#     Save extracted chunks to a JSON file for visualization and analysis.
#     """
#     with open(output_path, "w", encoding="utf-8") as json_file:
#         json.dump(chunks, json_file, ensure_ascii=False, indent=4)
#     print(f"Chunks saved to JSON file: {output_path}")
    
# import fitz  # PyMuPDF
# from PIL import Image
# from io import BytesIO

# def enrich_table_chunks(chunks, pdf_path, prompt_path,config):
#     """
#     For each table chunk in the provided chunks, this function extracts the corresponding page image 
#     from the PDF as a PIL object and sends it to Gemini using the ask_gemini_with_images function 
#     along with a prompt. The Gemini output (improved table extraction) is then added to the chunk.

#     Parameters:
#         chunks (list): List of chunk dictionaries (each with keys like "type", "content", "page", "length").
#         pdf_path (str): Path to the original PDF file.
#         prompt_path (str): Path to the prompt file used by the ask_gemini_with_images function.

#     Returns:
#         list: The updated list of chunks with enriched table data.
#     """
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

#                 # Convert bytes to PIL Image object
#                 img_pil = Image.open(BytesIO(img_bytes))
                
#                 # Call ask_gemini_with_images with the PIL image and prompt_path.
#                 gemini_output = ask_gemini_with_image(img_pil,prompt_path,key = config["model"]["key"])

#                 # Save the output from Gemini into the chunk.
#                 chunk["table_content"] = gemini_output
#                 chunk["content"] = extract_caption(gemini_output)
#             except Exception as e:
#                 print(f"Error processing table chunk on page {page_num}: {e}")

#     doc.close()
#     return chunks

# # def main():
# #     pdf_path = "./training_studies/NCT02799602_Hussain_ARASENS_JCO'23.pdf"
# #     json_output_path = "db/enhanced_chunks.json"

# #     if os.path.exists(pdf_path):
# #         print(f"Processing PDF: {pdf_path}")
# #         chunks = chunking(pdf_path)
        
# #         save_chunks_to_json(chunks, json_output_path)
# #     else:
# #         print(f"PDF file not found at: {pdf_path}")

# # main()



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

def semantic_text_chunking(text, min_size=1000):
    doc = nlp(text)
    chunks = []
    current_chunk = ""

    for sent in doc.sents:
        if len(current_chunk) < min_size:
            current_chunk += " " + sent.text.strip()
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sent.text.strip()

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def looks_like_inline_table(text):
    lines = text.split("\n")
    if len(lines) < 3:
        return False
    digit_lines = sum(1 for line in lines if re.search(r'\d', line) and re.search(r'\(.+\)', line))
    return digit_lines / len(lines) > 0.5

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
        table_doc = pdfplumber.open(pdf_path)

        for page_num in range(len(text_doc)):
            page_chunks = []
            raw_text = text_doc[page_num].get_text("text")

            if raw_text.strip():
                for chunk in semantic_text_chunking(raw_text):
                    chunk_type = "text"
                    if looks_like_inline_table(chunk):
                        chunk_type = "table"
                    page_chunks.append({
                        "type": chunk_type,
                        "content": chunk,
                        "page": page_num + 1,
                        "length": len(chunk)
                    })

            table_chunks = extract_tables_for_page(table_doc.pages[page_num])
            for table in table_chunks:
                page_chunks.append({
                    "type": "table",
                    "content": table,
                    "page": page_num + 1,
                    "length": len(table)
                })

            image_chunks = extract_images_for_page(text_doc[page_num], page_num + 1)
            page_chunks.extend(image_chunks)

            chunks.extend(page_chunks)

        text_doc.close()
        table_doc.close()

    except Exception as e:
        print(f"Chunking failed: {e}")

    return chunks

def save_chunks_to_json(chunks, output_path):
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(chunks, json_file, ensure_ascii=False, indent=4)
    print(f"Chunks saved to JSON file: {output_path}")

def enrich_table_chunks(chunks, pdf_path, prompt_path, config):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF file: {e}")
        return chunks

    for chunk in chunks:
        if chunk.get("type") == "table":
            page_num = chunk.get("page")
            if page_num is None:
                continue
            try:
                page = doc[page_num - 1]
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")
                img_pil = Image.open(BytesIO(img_bytes))
                gemini_output = ask_gemini_with_image(img_pil, prompt_path, key=config["model"]["key"])
                chunk["table_content"] = gemini_output
                chunk["content"] = extract_caption(gemini_output)
            except Exception as e:
                print(f"Error processing table chunk on page {page_num}: {e}")

    doc.close()
    return chunks