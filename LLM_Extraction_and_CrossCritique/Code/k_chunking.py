import fitz  # PyMuPDF for text and image extraction
import camelot  # For table extraction
import os
import json
import base64
import spacy
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

    # Split text into sentences and form meaningful chunks
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


def chunking(pdf_path):
    """
    Extract and segment the document into semantic text chunks, tables, and images.
    """
    chunks = []
    try:
        # Open the PDF document
        doc = fitz.open(pdf_path)

        # Extract and process text sections using semantic chunking
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
            print(f"Error extracting tables: {e}")

        # Extract images and associate them with their pages
        for page_num, page in enumerate(doc, start=1):
            images = page.get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                chunks.append({
                    "type": "image",
                    "content": f"Image of size {len(image_base64)} characters (Base64)",
                    "page": page_num,
                    "length": len(image_base64)
                })

    except Exception as e:
        print(f"Error processing PDF: {e}")

    return chunks


def check_chunk_quality(chunks):
    """
    Analyze chunk quality by providing insights into size, type, and coverage.
    """
    text_chunks = [chunk for chunk in chunks if chunk["type"] == "text"]
    table_chunks = [chunk for chunk in chunks if chunk["type"] == "table"]
    image_chunks = [chunk for chunk in chunks if chunk["type"] == "image"]

    print("\n=== Chunk Quality Report ===")
    print(f"Total Chunks: {len(chunks)}")
    print(f"Text Chunks: {len(text_chunks)}")
    print(f"Table Chunks: {len(table_chunks)}")
    print(f"Image Chunks: {len(image_chunks)}")

    if text_chunks:
        text_lengths = [chunk["length"] for chunk in text_chunks]
        print(f"Text Chunk Sizes - Min: {min(text_lengths)}, Max: {max(text_lengths)}, Avg: {sum(text_lengths)//len(text_lengths)}")

    if table_chunks:
        table_lengths = [chunk["length"] for chunk in table_chunks]
        print(f"Table Chunk Sizes - Min: {min(table_lengths)}, Max: {max(table_lengths)}, Avg: {sum(table_lengths)//len(table_lengths)}")

    if image_chunks:
        image_lengths = [chunk["length"] for chunk in image_chunks]
        print(f"Image Chunk Sizes - Min: {min(image_lengths)}, Max: {max(image_lengths)}, Avg: {sum(image_lengths)//len(image_lengths)}")

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
    # Path to the PDF
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


####### Add OCR to Image Processing

# import pytesseract
# from PIL import Image
# import io

# def extract_images_and_ocr(pdf_path):
#     """ Extracts images and applies OCR. """
#     image_chunks = []
#     doc = fitz.open(pdf_path)

#     for page_num, page in enumerate(doc, start=1):
#         images = page.get_images(full=True)
#         for img in images:
#             xref = img[0]
#             base_image = doc.extract_image(xref)
#             image_bytes = base_image["image"]

#             # Convert image bytes to PIL image
#             image = Image.open(io.BytesIO(image_bytes))

#             # Apply OCR
#             ocr_text = pytesseract.image_to_string(image)

#             image_chunks.append({
#                 "type": "image",
#                 "content": ocr_text if ocr_text.strip() else "Image extracted",
#                 "page": page_num,
#                 "length": len(image_bytes)
#             })

#     return image_chunks





# def extract_using_llms(model, model_key, pdf_folder_path, variable_file_path):
#     """
#     Main function to process PDFs using semantic chunking and LLMs.
#     """
#     # Read variable definitions (this remains unchanged)
#     df = pd.read_excel(variable_file_path, sheet_name='Definitions')
#     variables = [
#         x + ":" + y + "How to extract:" + z 
#         for x, y, z in zip(df['Column Name'], df['Definition'], df['Procedure'])
#     ]

#     pdf_folder_path = pdf_folder_path + "/"
#     semantic_chunks = []

#     # Perform semantic chunking on each PDF
#     for pdf_file in os.listdir(pdf_folder_path):
#         if pdf_file.endswith(".pdf"):
#             pdf_path = os.path.join(pdf_folder_path, pdf_file)
#             chunks = chunking(pdf_path)
#             semantic_chunks.extend(chunks)

#     print(f"Semantic chunking completed. Total chunks: {len(semantic_chunks)}")

#     # Process each semantic chunk with the LLM
#     results = []
#     for chunk in semantic_chunks:
#         prompt = prompt_design(chunk)  # Create a prompt based on the chunk
#         response = call_llm(model, model_key, prompt)  # Send prompt to LLM
#         results.append(response)

#     # Save raw responses
#     write_raw_responses(results, f"{model}_raw_responses.txt")
#     print("\nRaw responses saved to file.")

#     # Post-process the responses
#     pp_resps = post_processing(f"{model}_raw_responses.txt", model_key, model)
#     write_raw_responses(pp_resps, f"{model}_post_processed_responses.txt")
#     print("\nPost-processed responses saved to file.")

#     return pp_resps


# def prompt_design(chunk):
#     # Generate a prompt for the LLM based on the type of chunk.
#     if chunk["type"] == "text":
#         prompt = f"Extract the relevant information from the following text:\n\n{chunk['content']}"
#     elif chunk["type"] == "table":
#         prompt = f"Analyze the following table and extract relevant variables:\n\n{chunk['content']}"
#     elif chunk["type"] == "image":
#         prompt = f"Describe the content of the image found on page {chunk['page']} of the document."
#     else:
#         prompt = "Unknown chunk type."

#     return prompt




