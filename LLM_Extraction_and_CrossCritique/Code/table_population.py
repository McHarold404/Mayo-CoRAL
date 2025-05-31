import os
import json
import time
import sys
from model_inference.gpt import ask_chatgpt  # Using ask_chatgpt with system prompt path
from model_inference.gemini import ask_gemini    # Using ask_gemini with system prompt path
from speculativeRetrieval import speculative_rag_pipeline  # Import your existing speculative retrieval
from utils import evaluate_post_processed_output,get_model_function,calculate_accuracy_and_append
from k_chunking import generate_context


def generate_dynamic_query(group_label, columns_info, config):
    """
    Generates a dynamic retrieval query for a group of columns.
    It calls ask_gemini with a system prompt (from a file) and the group’s column definitions as the text.
    """
    # Create a string representation of the definitions for the group.
    definitions_text = "\n".join(
        [f"Find the value of {col['Definition']}" for col in columns_info]
    )
    return definitions_text


import os
import json
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

def populate_table_row(document_name, definitions_groups, chunks, config):
    """
    Multi-threaded version of populate_table_row.
    
    Processes each group (label) concurrently:
      1. Generates a dynamic query for the group.
      2. Runs the speculative retrieval pipeline on the document chunks.
      3. Maps the group answer to each column in that group.
    
    For each group:
      - Saves a .txt file with column info and retrieved chunks (up to 5) for verification.
      - Updates a shared running_outputs.txt with the final answer.
    
    Finally, saves the final table row to document.json, performs post processing, and runs evaluation.
    """
    table_row = {}
    
    print(f"Processing document: {document_name}")
    print(f"Total groups to process: {len(definitions_groups)}")
    
    # Ensure output directory exists
    output_dir = os.path.join(config["output_dir"], document_name)
    os.makedirs(output_dir, exist_ok=True)
    
    model_fn = get_model_function(config["model"]["type"])
    
    # Define a path for the running outputs file.
    running_outputs_path = os.path.join(output_dir, "running_outputs.txt")
    
    # Load previous running outputs if available.
    running_outputs = {}
    if os.path.exists(running_outputs_path):
        with open(running_outputs_path, "r", encoding="utf-8") as f:
            try:
                running_outputs = json.load(f)
            except Exception:
                running_outputs = {}
    context = generate_context(pdf_path=os.path.join("training_studies", f"{document_name}.pdf"), prompt_path=config["prompts"]["context_prompt"], config=config)
    print("CONTEXT GENERATED FOR DOCUMENT:")
    print("--------------------------")
    print(context)    
    print("--------------------------")
    # Lock to synchronize access to shared resources (running_outputs and table_row)
    lock = Lock()
    
    def sanitize_filename(filename):
        return re.sub(r'[\/\\:*?"<>|]', '_', filename)
    
    def process_group(group_label, columns_info):
        nonlocal running_outputs, table_row
        
        group_file_path = os.path.join(output_dir, f"{sanitize_filename(group_label)}.txt")
        # If the group file exists, skip reprocessing.
        if os.path.exists(group_file_path):
            print(f"Group '{group_label}' already processed. Skipping.")
            with lock:
                if group_label in running_outputs:
                    table_row[group_label] = running_outputs[group_label]
            return
        
        if config["model"]["type"] == 'gemini':
            time.sleep(60)  # Simulate wait time for dynamic query generation
        
        print(f"Processing group: {group_label}, columns: {len(columns_info)}")
        
        # Generate dynamic query for this group.
        query = generate_dynamic_query(group_label, columns_info, config)
        
        # (Optional) Process table chunks if needed; the original code filters for type 'table'
        # table_chunks = [chunk for chunk in chunks if chunk['type'] == 'table']
        
        # Run the speculative retrieval pipeline for the current group.
        sampled_chunks, candidate_answers, group_answer = speculative_rag_pipeline(pdf_path=os.path.join("training_studies", f"{document_name}.pdf"),
            context = context,retreival_query=query, chunks=chunks, columns_info=columns_info, config=config)
        
        # Update shared data structures in a thread-safe way.
        with lock:
            table_row[group_label] = group_answer
            running_outputs[group_label] = group_answer
        
        # Prepare text file content for verification.
        file_content = f"Group: {group_label}\n\n"
        file_content += "Column Info:\n"
        file_content += json.dumps(columns_info, indent=4, ensure_ascii=False) + "\n\n"
        file_content += "Retrieved Chunks and Answers Generated from Each:\n"
        for i, chunk in enumerate(sampled_chunks):
            file_content += f"Chunk {i+1}:\n{chunk['content']}\n\n"
            file_content += f"Answer {i+1}:\n{candidate_answers[i]}\n\n"
        file_content += f"Selected Answer:\n{group_answer}\n\n"
        
        # Write the group-specific file.
        with open(group_file_path, "w", encoding="utf-8") as f:
            f.write(file_content)
        print(f"Group details saved to: {group_file_path}")
        
        # Update running_outputs file (synchronized)
        with lock:
            with open(running_outputs_path, "w", encoding="utf-8") as f:
                json.dump(running_outputs, f, indent=4, ensure_ascii=False)
        
        print(f"Group '{group_label}' processed.")
    
    # Use a thread pool to process each group concurrently.
    with ThreadPoolExecutor() as executor:
        futures = []
        for group_label, columns_info in definitions_groups.items():
            futures.append(executor.submit(process_group, group_label, columns_info))
        # Wait for all group tasks to complete.
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing a group: {e}")
    
    # Save the final table row to a JSON file.
    output_path = os.path.join(output_dir, "document.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(table_row, f, ensure_ascii=False, indent=4)
    print(f"Final table row saved to: {output_path}")
    
    ## Post Processing and saving the final output
    pp_output_path = os.path.join(output_dir, "document_pp.txt")


#k adds
    if not os.path.exists(running_outputs_path):
        print(f"[WARN] Missing {running_outputs_path}. Cannot proceed with post-processing.")
        return table_row  # Or you could raise an error if post-processing is required
    
#k adds

    # Reload running outputs from file to ensure all groups are included.
    with open(running_outputs_path, "r", encoding="utf-8") as f:
        running_outputs = json.load(f)
    table_string = json.dumps(running_outputs, indent=2)
    pp_output = model_fn(
        text=table_string,
        prompt_path=config["prompts"]["post_processing"],
        key=config["model"]["key"]
    )
    with open(pp_output_path, "w", encoding="utf-8") as f:
        f.write(pp_output)
        
    print(f"Final post processed table row saved to: {pp_output_path}")
    
    # Evaluate the post-processed output.
    full_document_name = document_name + ".pdf"
    gold_csv_file = "GoldTable.csv"
    print("Evaluating...")    
    result = evaluate_post_processed_output(
        document_name=full_document_name,
        post_processed_text=pp_output,
        gold_csv_file=gold_csv_file,
        prompt_path=config["prompts"]["evaluation_prompt"],
        config=config
    )
    evaluation_path = os.path.join(output_dir, "evaluation_results.txt")
    with open(evaluation_path, "w", encoding="utf-8") as f:
        f.write(result)
    calculate_accuracy_and_append(evaluation_path)
    print(f"Evaluation results saved to: {evaluation_path}")
    
    return table_row
