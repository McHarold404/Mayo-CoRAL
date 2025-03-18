from document_chunker import process_document
from definitions import load_definitions
from table_population import populate_table_row

def main():
    # Global variable: set the document name (without .pdf extension)
    document_name = "NCT00309985_Sweeney_CHAARTED_NEJM'15"  # Replace with your actual document name
    
    # Step 1: Process the document (chunking + storing hybrid_chunks.json)
    chunks = process_document(document_name)
    
    # Step 2: Load the column definitions from Definitions.csv and group them by label
    definitions_groups = load_definitions("Definitions.csv")
    # Step 3: For each group, run the retrieval pipeline and populate the final table row.
    table_row = populate_table_row(document_name, definitions_groups, chunks)
    
    print("Final Table Row:")
    print(table_row)

if __name__ == "__main__":
    main()
