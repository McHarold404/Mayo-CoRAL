import os
import json
from model_inference.gpt import ask_chatgpt # Using ask_gemini with system prompt path
from model_inference.gemini import ask_gemini  # Using ask_gemini with system prompt path
import time
from speculativeRetrieval import speculative_rag_pipeline  # Import your existing speculative retrieval

def generate_dynamic_query(group_label, columns_info):
    """
    Generates a dynamic retrieval query for a group of columns.
    It calls ask_gemini with a system prompt (from a file) and the group’s column definitions as the text.
    """
    # Create a string representation of the definitions for the group.
    definitions_text = "\n".join(
        [f"{col['Column Name']}: {col['Definition']}" for col in columns_info]
    )
    
    # Set the path for the system prompt file containing the detailed extraction instructions.
    system_prompt_path = "prompts/dynamic_query_prompt.txt"
    
    # Call ask_gemini using the system prompt (from file) and the group definitions as text.
    dynamic_query = ask_gemini(prompt_path=system_prompt_path, text=definitions_text, key=1)
    
    return dynamic_query.strip()

def populate_table_row(document_name, definitions_groups, chunks):
    """
    For each group (label) in the definitions:
      1. Generate a dynamic query for the group.
      2. Run the speculative retrieval pipeline on the document chunks.
      3. Map the group answer to each column in that group.
      
    Save the final table row (as a dict) to db/{document_name}/document.json.
    """
    table_row = {}
    
    print(f"Processing document: {document_name}")
    print(f"Total groups to process: {len(definitions_groups)}")
    cnt = 0
    for group_label, columns_info in definitions_groups.items():
        # Generate a dynamic query based on the group's definitions using ask_gemini.
        time.sleep(30)
        print(cnt)
        cnt += 1
        print(f"Processing group: {group_label}, columns: {len(columns_info)}")
        query = generate_dynamic_query(group_label, columns_info)

        group_answer = speculative_rag_pipeline(query, chunks, columns_info)
        #print(f"Retrieved answer for group '{group_label}': {group_answer}")
        
        # Map the same answer to each column in this group.
        table_row[group_label] = group_answer
        # for col in columns_info:
        #     table_row[col["Column Name"]] = group_answer
        
        print(f"Group '{group_label}' processed.")
        
    # Save the final table row to a JSON file.
    output_dir = os.path.join("db", document_name)
    output_path = os.path.join(output_dir, "document.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(table_row, f, ensure_ascii=False, indent=4)
    
    print(f"Final table row saved to: {output_path}")
    return table_row
