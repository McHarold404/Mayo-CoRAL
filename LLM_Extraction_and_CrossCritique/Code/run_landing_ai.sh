#!/bin/bash

conda activate mayo
# List of documents to process
documents=(
    "NCT02799602_Hussain_ARASENS_JCO'23"
    "NCT00104715_Gravis_GETUG_EU'15"
    "NCT00268476_Attard_STAMPEDE_Lancet'23"
    "NCT00268476_James_STAMPEDE_IJC'22"
    "NCT00309985_Kriayako_CHAARTED_JCO'18"
    "NCT01809691_Aggarwal_SWOG1216_JCO'22"
)

# Directory where the scripts are located
# echo "Starting processing with main.py for all documents..."

# # Run main.py for each document
# for doc in "${documents[@]}"; do
#     echo "Processing $doc with main.py..."
#     python "$SCRIPT_DIR/main.py" --document_name "$doc.pdf" --key 1
#     if [ $? -eq 0 ]; then
#         echo "Successfully processed $doc with main.py"
#     else
#         echo "Error processing $doc with main.py"
#     fi
# done

# echo "Completed processing with main.py. Starting processing with extract_data_landing_ai_api.py..."

# Run extract_data_landing_ai_api.py for each document
for doc in "${documents[@]}"; do
    echo "Processing $doc with extract_data_landing_ai_api.py..."
    python "extract_data_landing_ai_api.py" --pdf_name "$doc.pdf"
    if [ $? -eq 0 ]; then
        echo "Successfully processed $doc with extract_data_landing_ai_api.py"
    else
        echo "Error processing $doc with extract_data_landing_ai_api.py"
    fi
done

echo "All processing completed."
