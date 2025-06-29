import re
from model_inference.gemini import ask_gemini
from model_inference.gpt import ask_chatgpt

def get_model_function(model_type):
    """Returns the appropriate model function based on the config."""
    if model_type.lower() == "gemini":
        return ask_gemini
    elif model_type.lower() == "gpt":
        return ask_chatgpt
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
def extract_caption(text):
    """
    Extracts the caption portion from the provided text.
    The caption is assumed to start after the "##Caption##" marker.
    
    Parameters:
        text (str): The full text containing the caption.
        
    Returns:
        str: The extracted caption text, stripped of any leading or trailing whitespace.
             Returns an empty string if the marker is not found.
    """
    # Use re.DOTALL so that the dot matches newline characters as well.
    pattern = r'##Caption##(.*)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ''

import re
import pandas as pd
import json

# Assume your custom ask_chatgpt function is defined elsewhere.
# def ask_chatgpt(prompt_path, text):
#     # Reads prompt template from prompt_path, appends text, then calls GPT.
#     ...

def extract_columns(post_processed_text):
    """
    Extract column names and their values from the post-processed output string.
    Expected format: Each line is "Column Name :: Value"
    Returns a dictionary of {column_name: value}.
    """
    pattern = r"^(.*?)\s*::\s*(.*)$"
    matches = re.findall(pattern, post_processed_text, re.MULTILINE)
    result = {}
    for key, value in matches:
        result[key.strip()] = value.strip()
    return result

def build_unified_mapping(filtered_gold, post_processed_output):
    """
    Build a unified mapping string that contains one line per column in the format:
    Column Name: Gold Value, Predicted Value
    Only columns that exist in the post-processed output are used.
    """
    lines = []
    for key in post_processed_output.keys():
        gold_value = filtered_gold.get(key, "not present")
        predicted_value = post_processed_output.get(key, "not present")
        lines.append(f"{key}: {gold_value}, {predicted_value}")
    return "\n".join(lines)

def evaluate_post_processed_output(document_name, post_processed_text, gold_csv_file, prompt_path,config):
    """
    Evaluates the post-processed output against the gold labels for a given document.
    Steps:
      1. Extract column–value pairs from the post-processed text using regex.
      2. Load gold labels from the CSV file and select the row matching the document name.
      3. Filter the gold labels to include only keys present in the post-processed output.
      4. Build a unified mapping string where each line is:
         Column Name: Gold Value, Predicted Value
      5. Construct a prompt that instructs the LLM to evaluate the mapping.
      6. Call ask_chatgpt(prompt_path, text) to perform the evaluation.
    
    Parameters:
      - document_name: The name of the document to evaluate.
      - post_processed_text: A multi-line string containing the post-processed output.
      - gold_csv_file: Path to the CSV file with gold labels.
      - prompt_path: Path to the prompt template file used by ask_chatgpt.
    
    Returns:
      - The evaluation result as returned by the LLM.
    """
    # Step 1: Extract post-processed column-value pairs.
    post_processed_output = extract_columns(post_processed_text)
    
    # Step 2: Load gold labels from CSV.
    df = pd.read_csv(gold_csv_file)
    # Step 3: Select the row matching the document name.

    gold_row = df.loc[(df['Document Name'] == document_name)] # & (df['Year'] == pub_year)

    if gold_row.empty:
        raise ValueError(f"No gold labels found for document: {document_name}")
    
    gold_labels = gold_row.iloc[0].to_dict()
    
    # Filter gold labels to only include keys that are present in post-processed output.
    filtered_gold_labels = {key: gold_labels[key] for key in post_processed_output.keys() if key in gold_labels}
    
    # Step 4: Build unified mapping string.
    unified_mapping = build_unified_mapping(filtered_gold_labels, post_processed_output)
    model_fn = get_model_function(config["model"]["type"])
    evaluation = model_fn(prompt_path = prompt_path,text = unified_mapping,key = config["model"]["key"])
    return evaluation

# with open("db/NCT02799602_Hussain_ARASENS_JCO'23/document_pp_only_tables.txt", "r", encoding="utf-8") as f:
#     pp_text = f.read()

# evaluation = evaluate_post_processed_output(document_name="NCT02799602_Hussain_ARASENS_JCO'23.pdf",
#                                 post_processed_text=pp_text,
#                                 gold_csv_file="GoldTable.csv",
#                                 prompt_path="prompts/evaluation_prompt.txt")

# with open("db/NCT02799602_Hussain_ARASENS_JCO'23/eval_only_tables.txt", "w", encoding="utf-8") as f:
#     f.write(evaluation)

import os 
import re
def calculate_accuracy_and_append(file_path: str) -> None:
    """
    Extended accuracy calculator with three outputs:
    
    1. Overall Accuracy
    2. Non-null Gold Accuracy
    3. A new file containing only non-null gold lines:
       "evaluation_results_non_null_only.txt" in the same folder as file_path.
    """
    NULL_TOKENS = {"nan", "not present", "n/a", "na", ""}
    value_pattern = re.compile(r":\s*(.*?)\s*vs\s*(.*?)\s*=>", re.IGNORECASE)

    correct = total = 0
    non_null_correct = non_null_total = 0
    non_null_lines = []

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        # 1. Overall accuracy logic
        if "Not Equivalent" in line:
            total += 1
        elif "Equivalent" in line:
            total += 1
            correct += 1

        # 2. Non-null evaluation logic
        match = value_pattern.search(line)
        if match:
            gold_val = match.group(1).strip()
            if gold_val.lower() not in NULL_TOKENS:
                non_null_total += 1
                non_null_lines.append(line)
                if "Equivalent" in line and "Not Equivalent" not in line:
                    non_null_correct += 1

    overall_acc = (correct / total * 100) if total else 0.0
    non_null_acc = (non_null_correct / non_null_total * 100) if non_null_total else 0.0

    summary = (
        f"\nTotal Evaluated Lines: {total}\n"
        f"Equivalent Lines: {correct}\n"
        f"Overall Accuracy: {overall_acc:.2f}%\n\n"
        f"Non-null Gold Lines: {non_null_total}\n"
        f"Non-null Correct Lines: {non_null_correct}\n"
        f"Non-null Accuracy: {non_null_acc:.2f}%"
    )

    # Append summary to the original file
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(summary)

    # Determine the output path for non-null lines
    output_dir = os.path.dirname(file_path)
    output_path = os.path.join(output_dir, "evaluation_results_non_null_only.txt")

    # Write non-null lines to new file
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(non_null_lines)
