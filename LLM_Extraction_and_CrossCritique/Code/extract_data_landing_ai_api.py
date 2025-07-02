import json
import requests
import os
from utils import evaluate_post_processed_output, get_model_function, calculate_accuracy_and_append

# API configuration
VA_API_KEY = "b2Q2ZTVyZTNkODNvc2lnc2gwbzluOmZSdE9EczQyRTNYZ2tMUUNpbXN4WmhNY1I2NllMbjQ5"  # Replace with your API key
headers = {"Authorization": f"Basic {VA_API_KEY}"}
url = "https://api.va.landing.ai/v1/tools/agentic-document-analysis"

# Paths configuration
base_pdf_path = "training_studies"  # Directory containing PDFs
schema_path = "old_definitions-schema.json"
output_base_dir = "landing_ai"
gold_csv_file = "GoldTable.csv"
config_file = "config.json"

# Create base output directory if it doesn't exist
os.makedirs(output_base_dir, exist_ok=True)

# Load the schema
with open(schema_path, "r") as file:
    schema = json.load(file)

# Load configuration for model evaluation and post-processing
with open(config_file, "r") as file:
    config = json.load(file)

# Function to process a single PDF
def process_pdf(pdf_path, pdf_name):
    # Create subdirectory for this PDF
    pdf_dir = os.path.join(output_base_dir, pdf_name.rsplit('.pdf', 1)[0])
    os.makedirs(pdf_dir, exist_ok=True)
    output_file = os.path.join(pdf_dir, f"{pdf_name}_extracted.json")
    
    # Check if the extracted file already exists
    if os.path.exists(output_file):
        print(f"Extracted data for {pdf_name} already exists at {output_file}. Skipping API call.")
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                extracted_info = json.load(f)
            return extracted_info
        except Exception as e:
            print(f"Error reading existing file for {pdf_name}: {str(e)}. Proceeding with API call.")
    
    files = [
        ("pdf", (pdf_name, open(pdf_path, "rb"), "application/pdf")),
    ]
    payload = {"fields_schema": json.dumps(schema)}
    
    try:
        response = requests.request("POST", url, headers=headers, files=files, data=payload)
        response_data = response.json()
        
        if "data" in response_data and "extracted_schema" in response_data["data"]:
            extracted_info = response_data["data"]["extracted_schema"]
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(extracted_info, f, indent=2)
            print(f"Data extracted from {pdf_name} and saved to {output_file}")
            return extracted_info
        else:
            print(f"Failed to extract data from {pdf_name}. Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error processing {pdf_name}: {str(e)}")
        return None

# Function to evaluate post-processed data against gold labels
def run_evaluation(pdf_name, post_processed_text):
    # Create subdirectory for this PDF
    pdf_dir = os.path.join(output_base_dir, pdf_name.rsplit('.pdf', 1)[0])
    os.makedirs(pdf_dir, exist_ok=True)
    
    eval_output_file = os.path.join(pdf_dir, f"{pdf_name}_evaluation.txt")
    
    # Ensure the document name for evaluation does not have '.pdf' appended twice
    full_pdf_name = pdf_name if pdf_name.endswith('.pdf') else pdf_name + ".pdf"
    try:
        evaluation_result = evaluate_post_processed_output(
            document_name=full_pdf_name,
            post_processed_text=post_processed_text,
            gold_csv_file=gold_csv_file,
            prompt_path=config["prompts"]["evaluation_prompt"],
            config=config
        )
        with open(eval_output_file, "w", encoding="utf-8") as f:
            f.write(evaluation_result)
        print(f"Evaluation results for {pdf_name} saved to {eval_output_file}")
        
        # Calculate accuracy and append results
        calculate_accuracy_and_append(eval_output_file)
        print(f"Accuracy calculated and appended for {pdf_name} to {eval_output_file}")
        
        # Read and display the updated content with accuracy metrics
        try:
            with open(eval_output_file, "r", encoding="utf-8") as f:
                updated_content = f.read()
            print(f"Updated evaluation content with accuracy metrics for {pdf_name}:")
            print(updated_content)
        except Exception as read_error:
            print(f"Error reading updated evaluation file for {pdf_name}: {str(read_error)}")
    except Exception as e:
        print(f"Error during evaluation of {pdf_name}: {str(e)}")

# Function to post-process and evaluate extracted data
def post_process_and_evaluate(pdf_name, extracted_data):
    # Convert extracted data to a formatted string, replacing blank values with "Nan"
    if "clinical_trial_data" in extracted_data and extracted_data["clinical_trial_data"]:
        # Use the first entry if multiple are extracted, or adjust as needed
        data_entry = extracted_data["clinical_trial_data"][0] if extracted_data["clinical_trial_data"] else {}
        
        # Create subdirectory for this PDF
        pdf_dir = os.path.join(output_base_dir, pdf_name.rsplit('.pdf', 1)[0])
        os.makedirs(pdf_dir, exist_ok=True)
        processed_output_file = os.path.join(pdf_dir, f"{pdf_name}_processed.txt")
        
        # Format the data directly from JSON, replacing empty values with "Nan"
        try:
            formatted_lines = []
            for key, value in data_entry.items():
                # Replace empty strings or None with "Nan"
                formatted_value = "Nan" if value == "" or value is None else value
                formatted_lines.append(f"{key}:: {formatted_value}")
            post_processed_text = "\n".join(formatted_lines)
            
            with open(processed_output_file, "w", encoding="utf-8") as f:
                f.write(post_processed_text)
            print(f"Post-processed data for {pdf_name} saved to {processed_output_file}")
            
            # Run evaluation on the post-processed output
            run_evaluation(pdf_name, post_processed_text)
        except Exception as e:
            print(f"Error during direct formatting of {pdf_name}: {str(e)}")
    else:
        print(f"No clinical trial data found in extracted output for {pdf_name}")

# Main function to process a single PDF specified by the user
def main(pdf_name):
    pdf_path = os.path.join(base_pdf_path, pdf_name)
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file {pdf_name} not found at {pdf_path}")
        return
    
    print(f"Processing {pdf_name}...")
    extracted_data = process_pdf(pdf_path, pdf_name)
    if extracted_data:
        post_process_and_evaluate(pdf_name, extracted_data)

# Temporary main function to run only post-processing and evaluation on existing extracted JSON
def temp_main_post_process(pdf_name):
    json_path = os.path.join(output_base_dir, pdf_name.rsplit('.pdf', 1)[0], f"{pdf_name}_extracted.json")
    if not os.path.exists(json_path):
        print(f"Error: Extracted JSON file for {pdf_name} not found at {json_path}")
        return
    
    print(f"Loading extracted data for {pdf_name} from {json_path}...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            extracted_data = json.load(f)
        if extracted_data:
            print(f"Running post-processing and evaluation for {pdf_name}...")
            post_process_and_evaluate(pdf_name, extracted_data)
        else:
            print(f"No data found in JSON file for {pdf_name}")
    except Exception as e:
        print(f"Error loading JSON for {pdf_name}: {str(e)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract clinical data from a specified PDF or run post-processing only.")
    parser.add_argument("--pdf_name", type=str, default="NCT00268476_Attard_STAMPEDE_Lancet'23.pdf", required=False, help="The name of the PDF file to process (e.g., NCT00268476_Clarke_SUBG_STAMPEDE_Ann Onc18.pdf)")
    parser.add_argument("--mode", type=str, choices=["extract", "postprocess"], default="extract", help="Mode to run: 'extract' for full processing, 'postprocess' for post-processing and evaluation only")
    args = parser.parse_args()
    
    if args.mode == "extract":
        main(args.pdf_name)
    elif args.mode == "postprocess":
        temp_main_post_process(args.pdf_name)
