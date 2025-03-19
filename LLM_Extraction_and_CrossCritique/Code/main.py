import json
from document_chunker import process_document
from definitions import load_definitions
from table_population import populate_table_row

def load_config(config_path="config.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    # Load configuration
    config = load_config()
    document_name = config["document_name"]
    
    # Step 1: Process the document (chunking + storing hybrid_chunks.json)
    chunks = process_document(document_name)
    
    # Step 2: Load the column definitions from Definitions.csv and group them by label
    definitions_groups = load_definitions(config["definitions_file"])
    
    # Step 3: Populate the table row, passing the config for model details
    table_row = populate_table_row(document_name, definitions_groups, chunks, config)
    
    print("Final Table Row:")
    print(table_row)

if __name__ == "__main__":
    main()