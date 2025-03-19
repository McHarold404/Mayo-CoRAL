import fitz  # PyMuPDF for text and image extraction
import camelot  # For table extraction
import os
import json
import base64
import spacy
import pytesseract
from PIL import Image
import io
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Load NLP model for text segmentation
nlp = spacy.load("en_core_web_sm")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")  # Lightweight model for semantic merging

def semantic_text_chunking(text, min_size=500, merge_threshold=0.8):
    """
    Uses NLP to split text into semantic chunks and merges similar chunks based on embeddings.
    """
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

    # Merge semantically similar chunks
    embeddings = embedding_model.encode(chunks)
    similarities = cosine_similarity(embeddings, embeddings)
    
    merged_chunks = []
    visited = set()

    for i, chunk in enumerate(chunks):
        if i in visited:
            continue
        similar = [chunk]

        for j in range(i+1, len(chunks)):
            if similarities[i][j] > merge_threshold:
                similar.append(chunks[j])
                visited.add(j)

        merged_chunks.append(" ".join(similar))

    return merged_chunks


def extract_table_ocr(image_bytes):
    """
    Use OCR to extract tables from images.
    """
    image = Image.open(io.BytesIO(image_bytes))
    ocr_text = pytesseract.image_to_string(image, config="--psm 6")  # psm 6 treats image as a single uniform block of text
    return ocr_text


def chunking(pdf_path):
    """
    Extract and segment the document into semantic text chunks, tables, and images.
    Now includes OCR for table extraction.
    """
    chunks = []
    try:
        doc = fitz.open(pdf_path)

        # Extract text using semantic chunking
        for page_num, page in enumerate(doc, start=1):
            raw_text = page.get_text("text")
            if raw_text.strip():
                text_chunks = semantic_text_chunking(raw_text)
                for chunk in text_chunks:
                    chunks.append({
                        "type": "text",
                        "content": chunk,
                        "page": page_num,
                        "length": len(chunk)
                    })

        # Extract tables using Camelot
        try:
            tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream")
            for i, table in enumerate(tables):
                table_str = table.df.to_string(index=False)
                chunks.append({
                    "type": "table",
                    "content": table_str,
                    "page": table.parsing_report['page'],
                    "length": len(table_str)
                })
        except Exception as e:
            print(f"Error extracting tables with Camelot: {e}")

        # Extract images and apply OCR for tables
        for page_num, page in enumerate(doc, start=1):
            images = page.get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Extract text from images (OCR for tables)
                ocr_text = extract_table_ocr(image_bytes)

                chunks.append({
                    "type": "image_table" if ocr_text.strip() else "image",
                    "content": ocr_text if ocr_text.strip() else "Image extracted",
                    "page": page_num,
                    "length": len(ocr_text) if ocr_text.strip() else len(image_bytes)
                })

    except Exception as e:
        print(f"Error processing PDF: {e}")

    return chunks


def check_chunk_quality(chunks):
    """
    Analyze chunk quality by providing insights into size, type, and coverage.
    """
    text_chunks = [chunk for chunk in chunks if chunk["type"] == "text"]
    table_chunks = [chunk for chunk in chunks if chunk["type"] in ["table", "image_table"]]
    image_chunks = [chunk for chunk in chunks if chunk["type"] == "image"]

    print("\n=== Chunk Quality Report ===")
    print(f"Total Chunks: {len(chunks)}")
    print(f"Text Chunks: {len(text_chunks)}")
    print(f"Table Chunks (Including OCR Extracted): {len(table_chunks)}")
    print(f"Image Chunks: {len(image_chunks)}")

    if text_chunks:
        text_lengths = [chunk["length"] for chunk in text_chunks]
        print(f"Text Chunk Sizes - Min: {min(text_lengths)}, Max: {max(text_lengths)}, Avg: {sum(text_lengths)//len(text_lengths)}")

    if table_chunks:
        table_lengths = [chunk["length"] for chunk in table_chunks]
        print(f"Table Chunk Sizes - Min: {min(table_lengths)}, Max: {max(table_lengths)}, Avg: {sum(table_lengths)//len(table_lengths)}")

    if image_chunks:
        image_lengths = [chunk["length"] for chunk in image_chunks]
        print(f"Image Chunk Sizes - Min: {min(image_lengths)}, Max: {max(image_lengths)}, Avg: {sum(image_lengths)//len(image_chunks)}")

    pages_covered = sorted(set(chunk["page"] for chunk in chunks))
    print(f"Pages Covered: {pages_covered}")


def save_chunks_to_json(chunks, output_path):
    """
    Save extracted chunks to a JSON file for visualization and analysis.
    """
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(chunks, json_file, ensure_ascii=False, indent=4)
    print(f"Chunks saved to JSON file: {output_path}")


def main():
    pdf_path = "NCT02799602_Hussain_ARASENS_JCO'23.pdf"
    json_output_path = "hybrid2_chunks.json"

    if os.path.exists(pdf_path):
        print(f"Processing PDF: {pdf_path}")
        chunks = chunking(pdf_path)

        check_chunk_quality(chunks)
        save_chunks_to_json(chunks, json_output_path)
    else:
        print(f"PDF file not found at: {pdf_path}")


if __name__ == "__main__":
    main()

