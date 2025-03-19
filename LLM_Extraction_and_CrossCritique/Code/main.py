# main.py
import json
from document_chunker import process_document
from definitions import load_definitions
from table_population import populate_table_row

def load_config(config_file="config.json"):
    """Load the configuration from a JSON file."""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file '{config_file}' not found.")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: Config file '{config_file}' is not a valid JSON file.")
        exit(1)

def main(config_file="config.json"):
    # Load the configuration
    config = load_config(config_file)
    
    # Extract settings from the config
    document_name = config["document_name"]
    definitions_file = config["definitions_file"]
    
    # Step 1: Process the document (chunking + storing hybrid_chunks.json)
    # Pass additional chunking settings if needed
    chunk_settings = config.get("chunk_settings", {})  # Default to empty dict if not present
    chunks = process_document(document_name, **chunk_settings)
    
    # Step 2: Load the column definitions from Definitions.csv and group them by label
    definitions_groups = load_definitions(definitions_file)
    
    # Step 3: For each group, run the retrieval pipeline and populate the final table row.
    table_row = populate_table_row(document_name, definitions_groups, chunks, config)
    
    print("Final Table Row:")
    print(table_row)

if __name__ == "__main__":
    main()