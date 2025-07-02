import os, fitz, json
from k_chunking import chunking, save_chunks_to_json, enrich_table_chunks  # Using your existing chunking functions
from k_chunking_structure_extractor import extract_document_structure, tag_chunks_with_sections


def process_document(document_name,config):
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

    # ---------- 2) NEW  section tagging --------------
    # try:
    #     section_map = extract_document_structure(pdf_path, config)
    #     print("Output Path,", output_dir)
    #     save_chunks_to_json(section_map,output_path=f"{output_dir}/section_map.json")
    #     #with open(f"{output_dir}/section_map.txt", "w", encoding="utf-8") as f:
    #     #    f.write(section_map)
    #     full_text   = "\n".join(page.get_text() for page in fitz.open(pdf_path))
    #     chunks      = tag_chunks_with_sections(chunks, section_map, full_text)
    # except Exception as e:
    #     print(f"[WARN] Section tagging skipped: {e}")
    # --------------------------------------------------
    prompt_paths = {"table": config["prompts"]["extract_table"],  # ✅ Added prompt for tables
                    "figure": config["prompts"]["extract_figure"]}  # ✅ Added prompt for figures
    enriched_chunks = enrich_table_chunks(chunks = chunks, pdf_path= pdf_path,prompt_paths= prompt_paths,config=config)
    save_chunks_to_json(enriched_chunks, output_path)
    
    print(f"Document processed and chunks saved to: {output_path}")
    return enriched_chunks


# def main():
#     document_name = "NCT02799602_Hussain_ARASENS_JCO'23"  # Replace with your actual document name
#     chunks = process_document(document_name)
#     print("Chunks processed and saved.")
    
# main()