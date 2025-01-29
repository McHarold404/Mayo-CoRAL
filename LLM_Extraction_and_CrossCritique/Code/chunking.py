import fitz  # PyMuPDF for text and image extraction
import camelot  # For table extraction
import os
import json
import base64

def chunking(pdf_path):
    """
    Extract and segment the document into semantic chunks of text, tables, and images.
    """
    chunks = []
    try:
        # Open the PDF document
        doc = fitz.open(pdf_path)

        # Extract text sections based on headers and paragraphs
        for page_num, page in enumerate(doc, start=1):
            blocks = page.get_text("blocks")  # Extract text as blocks
            text_content = ""
            for block in sorted(blocks, key=lambda b: (b[1], b[0])):  # Sort by vertical and horizontal position
                if block[4].strip():  # Check if block has non-empty content
                    text_content += block[4].strip() + " "  # Merge blocks into one chunk

            if text_content.strip():
                chunks.append({
                    "type": "text",
                    "content": text_content.strip(),
                    "page": page_num,
                    "length": len(text_content.strip())
                })

        # Extract tables using Camelot
        try:
            tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream")  # Adjust flavor if needed
            for i, table in enumerate(tables):
                table_str = table.df.to_string(index=False)
                chunks.append({
                    "type": "table",
                    "content": table_str,  # Convert table DataFrame to string
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
                    "content": f"Image of size {len(image_base64)} characters (Base64)",  # Metadata for analysis
                    "page": page_num,
                    "length": len(image_base64)  # Add Base64 size for analysis
                })

    except Exception as e:
        print(f"Error processing PDF: {e}")

    return chunks

def check_chunk_quality(chunks):
    """
    Analyze chunk quality by providing insights into size, type, and coverage.
    """
    # Summary variables
    text_chunks = [chunk for chunk in chunks if chunk["type"] == "text"]
    table_chunks = [chunk for chunk in chunks if chunk["type"] == "table"]
    image_chunks = [chunk for chunk in chunks if chunk["type"] == "image"]

    print("\n=== Chunk Quality Report ===")
    print(f"Total Chunks: {len(chunks)}")
    print(f"Text Chunks: {len(text_chunks)}")
    print(f"Table Chunks: {len(table_chunks)}")
    print(f"Image Chunks: {len(image_chunks)}")

    # Check text chunk sizes
    if text_chunks:
        text_lengths = [chunk["length"] for chunk in text_chunks]
        print(f"Text Chunk Sizes - Min: {min(text_lengths)}, Max: {max(text_lengths)}, Avg: {sum(text_lengths)//len(text_lengths)}")

    # Check table chunk sizes
    if table_chunks:
        table_lengths = [chunk["length"] for chunk in table_chunks]
        print(f"Table Chunk Sizes - Min: {min(table_lengths)}, Max: {max(table_lengths)}, Avg: {sum(table_lengths)//len(table_lengths)}")

    # Check image chunk sizes
    if image_chunks:
        image_lengths = [chunk["length"] for chunk in image_chunks]
        print(f"Image Chunk Sizes - Min: {min(image_lengths)}, Max: {max(image_lengths)}, Avg: {sum(image_lengths)//len(image_lengths)}")

    # Pages covered
    pages_covered = sorted(set(chunk["page"] for chunk in chunks))
    print(f"Pages Covered: {pages_covered}")


def save_chunks_to_json(chunks, output_path):
    """
    Save extracted chunks to a JSON file for visualization and analysis.
    """
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(chunks, json_file, ensure_ascii=False, indent=4)
    print(f"Chunks saved to JSON file: {output_path}")

def visualize_chunks(chunks, num_samples=5):
    """
    Display a preview of the extracted chunks for quality analysis.
    """
    print(f"\n=== Total Chunks: {len(chunks)} ===")
    print(f"Previewing the first {num_samples} chunks:\n")
    for idx, chunk in enumerate(chunks[:num_samples]):
        print(f"Chunk {idx + 1}:")
        print(f"  Type: {chunk['type']}")
        print(f"  Page: {chunk['page']}")
        if chunk["type"] == "text":
            print(f"  Content: {chunk['content'][:200]}...")  # Show first 200 chars
        elif chunk["type"] == "table":
            print(f"  Content: (Table of {chunk['length']} characters)")
        elif chunk["type"] == "image":
            print(f"  Content: (Image of {chunk['length']} bytes)")
        print("-" * 40)


def main():
    # Path to the PDF
    pdf_path = "NCT02799602_Hussain_ARASENS_JCO'23.pdf"
    json_output_path = "chunks.json"

    # Check if the file exists
    if os.path.exists(pdf_path):
        print(f"Processing PDF: {pdf_path}")
        # Call the chunking function
        chunks = chunking(pdf_path)

        # Check and analyze chunk quality
        check_chunk_quality(chunks)

        # Save chunks to JSON
        save_chunks_to_json(chunks, json_output_path)

        # Visualize a sample of chunks
        visualize_chunks(chunks, num_samples=10)  # Show first 10 chunks for review

        # # Display a few chunks for a quick preview
        # print("\n=== Chunk Preview ===")
        # for chunk in chunks[:5]:  # Show only the first 5 chunks for brevity
        #     print(chunk)
    else:
        print(f"PDF file not found at: {pdf_path}")

if __name__ == "__main__":
    main()



# ##### this have to replace

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




