import os
import json
from model_inference.gpt import ask_chatgpt # Using ask_gemini with system prompt path
from model_inference.gemini import ask_gemini  # Using ask_gemini with system prompt path
import time
from speculativeRetrieval import speculative_rag_pipeline  # Import your existing speculative retrieval
from utils import evaluate_post_processed_output
def generate_dynamic_query(group_label, columns_info):
    """
    Generates a dynamic retrieval query for a group of columns.
    It calls ask_gemini with a system prompt (from a file) and the group’s column definitions as the text.
    """
    # Create a string representation of the definitions for the group.
    definitions_text = "\n".join(
        [f"Find the value of {col['Column Name']}: {col['Definition']}" for col in columns_info]
    )
    return definitions_text
    # Set the path for the system prompt file containing the detailed extraction instructions.
    # system_prompt_path = "prompts/dynamic_query_prompt.txt"
    
    # # Call ask_gemini using the system prompt (from file) and the group definitions as text.
    # dynamic_query = ask_gemini(prompt_path=system_prompt_path, text=definitions_text)
    
    # return dynamic_query.strip()
import os
import json
import time

def populate_table_row(document_name, definitions_groups, chunks):
    """
    For each group (label) in the definitions:
      1. Generate a dynamic query for the group.
      2. Run the speculative retrieval pipeline on the document chunks.
      3. Map the group answer to each column in that group.
      
    Save the final table row (as a dict) to db/{document_name}/document.json.
    Also, for each group, save a .txt file (named by the group label) in the same directory
    that contains the column info and the retrieved chunks (up to 5) for verification.
    """
    table_row = {}
    
    print(f"Processing document: {document_name}")
    print(f"Total groups to process: {len(definitions_groups)}")
    cnt = 0
    
    # Ensure output directory exists
    output_dir = os.path.join("db", document_name)
    os.makedirs(output_dir, exist_ok=True)
    
    for group_label, columns_info in definitions_groups.items():
        time.sleep(30)  # Simulate wait time for dynamic query generation
        print(cnt)
        cnt += 1
        print(f"Processing group: {group_label}, columns: {len(columns_info)}")
        
        # Generate dynamic query for this group
        query = generate_dynamic_query(group_label, columns_info)
        table_chunks = [chunk for chunk in chunks if chunk['type'] == 'table']
        # Run the speculative retrieval pipeline for the current group.
        sampled_chunks,group_answer = speculative_rag_pipeline(retreival_query=query, chunks= chunks, columns_info=columns_info)
        
        # Map the answer to the group label in the final table row.
        table_row[group_label] = group_answer
        print(f"Group '{group_label}' processed.")
        
        # Prepare text file content.
        file_content = f"Group: {group_label}\n\n"
        file_content += "Column Info:\n"
        file_content += json.dumps(columns_info, indent=4, ensure_ascii=False) + "\n\n"
        file_content += "Retrieved Chunks:\n"
        
        for i, chunk in enumerate(sampled_chunks):
                file_content += f"Chunk {i+1}:\n{chunk['content']}\n\n"

        def sanitize_filename(filename):
            import re
            # Replace invalid characters (/, \, :, *, ?, ", <, >, |) with an underscore
            return re.sub(r'[\/\\:*?"<>|]', '_', filename)

        group_file_path = os.path.join(output_dir, f"{sanitize_filename(group_label)}.txt")
        # Save the text file for this group.
        
        # group_file_path = os.path.join(output_dir, f"{group_label.replace("/",)}.txt")
        with open(group_file_path, "w", encoding="utf-8") as f:
            f.write(file_content)
        print(f"Group details saved to: {group_file_path}")
    
    # Save the final table row to a JSON file.
    output_path = os.path.join(output_dir, "document.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(table_row, f, ensure_ascii=False, indent=4)
    print(f"Final table row saved to: {output_path}")
    
    ## Post Processing and saving the final output
    pp_output_path = os.path.join(output_dir, "document_pp.txt")
    table_string = json.dumps(table_row, indent=2)
    pp_output = ask_gemini(text = table_string,prompt_path="prompts/post_processing.txt")
    with open(pp_output_path, "w", encoding="utf-8") as f:
        f.write(pp_output)
        
    print(f"Final post processed table row saved to: {pp_output_path}")
    
    # Evaluate the post-processed output    
    full_document_name = document_name + ".pdf"
    gold_csv_file = "GoldTable.csv"
    print("Evaluating...")    
    result = evaluate_post_processed_output(document_name = full_document_name,post_processed_text=pp_output,gold_csv_file = gold_csv_file, prompt_path = "prompts/evaluation_prompt.txt")
    with open(os.path.join(output_dir, "evaluation_results.txt"), "w", encoding="utf-8") as f:
        f.write(result)
    return table_row