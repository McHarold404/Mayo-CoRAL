import os
import json
from k_chunking import chunking, check_chunk_quality, save_chunks_to_json  # Using your existing chunking functions

def process_document(document_name):
    """
    Processes a single document by:
      1. Checking if hybrid_chunks.json already exists in db/{document_name}.
         If it does, load and return the chunks.
      2. Otherwise, reads {document_name}.pdf from the training_studies folder,
         chunks it using the existing chunking code,
         and stores the chunks in db/{document_name}/hybrid_chunks.json.
      
    Returns the list of chunks.
    """
    # Construct file paths
    pdf_path = os.path.join("training_studies", f"{document_name}.pdf")
    output_dir = os.path.join("db", document_name)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "hybrid_chunks.json")
    
    # Check if the chunks file already exists
    if os.path.exists(output_path):
        print(f"Chunks already exist for {document_name}. Loading from {output_path}")
        with open(output_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        return chunks
    
    # Process document using the existing chunking code
    chunks = chunking(pdf_path)
    save_chunks_to_json(chunks, output_path)
    
    print(f"Document processed and chunks saved to: {output_path}")
    return chunks