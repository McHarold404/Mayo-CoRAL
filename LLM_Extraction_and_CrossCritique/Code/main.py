import json
from document_chunker import process_document
from definitions import load_definitions
from table_population import populate_table_row
from token_tracker import get_total_cost
import argparse


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config

def main(config):

    document_name = config["document_name"]
    
    # Step 1: Process the document (chunking + storing hybrid_chunks.json)
    chunks = process_document(document_name,config=config)
    
    # Step 2: Load the column definitions from Definitions.csv and group them by label
    definitions_groups = load_definitions(config["definitions_file"])
    
    # Step 3: Populate the table row, passing the config for model details
    table_row = populate_table_row(document_name, definitions_groups, chunks, config)
    
    print("Final Table Row:")
    print(table_row)
    total_cost = get_total_cost()
    print("Total Cost in Dollars:", total_cost)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the extraction pipeline.")
    parser.add_argument("--document_name", type=str, required=True, help="The name of the document to process.")
    parser.add_argument("--key", type=int, required=True, help="The model key to use.")
    parser.add_argument("--config", type=str, default="config.json", help="Path to the config file.")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    # Replace the placeholders with command-line arguments
    config["document_name"] = args.document_name
    config["model"]["key"] = args.key
    main(config= config)