# import fitz  # PyMuPDF for text and image extraction
# import camelot  # For table extraction
# import pdfplumber  # Alternative table extraction
# import os
# import json
# import base64
# import spacy
# import pandas as pd
# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity

# # Load NLP model for text segmentation
# nlp = spacy.load("en_core_web_sm")
# embedding_model = SentenceTransformer("all-MiniLM-L6-v2")  # Lightweight model for semantic merging

# def semantic_text_chunking(text, min_size=500, merge_threshold=0.8):
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
#     Extract tables using both Camelot and PDFPlumber for improved accuracy.
#     """
#     extracted_tables = []
    
#     # Try Camelot with lattice mode first
#     try:
#         tables = camelot.read_pdf(pdf_path, pages="all", flavor="lattice")
#         for i, table in enumerate(tables):
#             table_df = table.df
#             if not table_df.empty:
#                 table_str = table_df.to_csv(index=False)
#                 extracted_tables.append({
#                     "type": "table",
#                     "content": table_str,
#                     "page": table.parsing_report['page'],
#                     "length": len(table_str)
#                 })
#     except Exception as e:
#         print(f"Error with Camelot lattice extraction: {e}")
    
#     # Use PDFPlumber as a fallback
#     try:
#         with pdfplumber.open(pdf_path) as pdf:
#             for page_num, page in enumerate(pdf.pages, start=1):
#                 for table in page.extract_tables():
#                     df = pd.DataFrame(table)
#                     table_str = df.to_csv(index=False)
#                     extracted_tables.append({
#                         "type": "table",
#                         "content": table_str,
#                         "page": page_num,
#                         "length": len(table_str)
#                     })
#     except Exception as e:
#         print(f"Error with PDFPlumber extraction: {e}")

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
#                 text_chunks = semantic_text_chunking(raw_text)
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


# def main():
#     pdf_path = "NCT02799602_Hussain_ARASENS_JCO'23.pdf"
#     json_output_path = "enhanced_chunks.json"

#     if os.path.exists(pdf_path):
#         print(f"Processing PDF: {pdf_path}")
#         chunks = chunking(pdf_path)
#         save_chunks_to_json(chunks, json_output_path)
#     else:
#         print(f"PDF file not found at: {pdf_path}")


# if __name__ == "__main__":
#     main()




import fitz  # PyMuPDF for text and image extraction
import camelot  # For table extraction
import pdfplumber  # Alternative table extraction
import os
import json
import base64
import spacy
import pandas as pd
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

def extract_tables(pdf_path):
    """
    Extract tables using Camelot first; if it fails, use PDFPlumber.
    """
    extracted_tables = []
    
    # Try Camelot first (works for vector-based PDFs)
    try:
        tables = camelot.read_pdf(pdf_path, pages="all", flavor="lattice")
        if tables.n > 0:
            for i, table in enumerate(tables):
                df = table.df
                markdown_table = df.to_markdown(index=False)
                extracted_tables.append({
                    "type": "table",
                    "content": markdown_table,
                    "page": table.parsing_report['page'],
                    "length": len(markdown_table)
                })
            return extracted_tables  # Return immediately if Camelot succeeds
    except Exception as e:
        print(f"Camelot failed: {e}")
    
    # If Camelot fails, use PDFPlumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables_on_page = page.extract_tables()
                if tables_on_page:
                    combined_table = ""
                    for table in tables_on_page:
                        df = pd.DataFrame(table)
                        header = df.iloc[0].tolist() if df.shape[0] > 1 else None
                        df = df[1:].reset_index(drop=True) if header else df
                        markdown_table = df.to_markdown(index=False, headers=header) if header else df.to_markdown(index=False)
                        combined_table += "\n\n" + markdown_table
                    extracted_tables.append({
                        "type": "table",
                        "content": combined_table.strip(),
                        "page": page_num,
                        "length": len(combined_table)
                    })
    except Exception as e:
        print(f"PDFPlumber failed: {e}")
    
    return extracted_tables

def extract_images(pdf_path):
    """ Extracts images and encodes them in Base64. """
    image_chunks = []
    doc = fitz.open(pdf_path)
    
    for page_num, page in enumerate(doc, start=1):
        images = page.get_images(full=True)
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            image_chunks.append({
                "type": "image",
                "content": f"Image of size {len(image_base64)} characters (Base64)",
                "page": page_num,
                "length": len(image_base64)
            })
    
    return image_chunks

def chunking(pdf_path):
    """
    Extract and segment the document into semantic text chunks, tables, and images.
    """
    chunks = []
    
    # Extract text
    try:
        doc = fitz.open(pdf_path)
        for page_num, page in enumerate(doc.pages, start=1):
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
    except Exception as e:
        print(f"Error extracting text: {e}")
    
    # Extract tables
    chunks.extend(extract_tables(pdf_path))
    
    # Extract images
    chunks.extend(extract_images(pdf_path))
    
    return chunks

def save_chunks_to_json(chunks, output_path):
    """
    Save extracted chunks to a JSON file for visualization and analysis.
    """
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(chunks, json_file, ensure_ascii=False, indent=4)
    print(f"Chunks saved to JSON file: {output_path}")

def main():
    pdf_path = "./training_studies/NCT02799602_Hussain_ARASENS_JCO'23.pdf"
    json_output_path = "db/enhanced_chunks.json"

    if os.path.exists(pdf_path):
        print(f"Processing PDF: {pdf_path}")
        chunks = chunking(pdf_path)
        save_chunks_to_json(chunks, json_output_path)
    else:
        print(f"PDF file not found at: {pdf_path}")

if __name__ == "__main__":
    main()