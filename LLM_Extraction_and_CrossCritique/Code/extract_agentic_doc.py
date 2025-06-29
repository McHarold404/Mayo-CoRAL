import os
import argparse
import json
from agentic_doc.parse import parse

# Paths configuration
base_pdf_path = "training_studies"  # Directory containing PDFs
output_base_dir = "landing_ai"

# Create base output directory if it doesn't exist
os.makedirs(output_base_dir, exist_ok=True)

# Function to process a single PDF using agentic_doc.parse
def process_pdf(pdf_name):
    pdf_path = os.path.join(base_pdf_path, pdf_name)
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file {pdf_name} not found at {pdf_path}")
        return
    
    # Create subdirectory for this PDF
    pdf_dir = os.path.join(output_base_dir, pdf_name.rsplit('.pdf', 1)[0])
    os.makedirs(pdf_dir, exist_ok=True)
    output_file = os.path.join(pdf_dir, f"{pdf_name}_agentic_doc_output.txt")
    
    # Check if both output files already exist
    markdown_file = os.path.join(pdf_dir, f"{pdf_name}_markdown.md")
    chunks_file = os.path.join(pdf_dir, f"{pdf_name}_chunks.txt")
    
    if os.path.exists(markdown_file) and os.path.exists(chunks_file):
        print(f"Output data for {pdf_name} already exists at {markdown_file} and {chunks_file}. Skipping processing.")
        return
    
    try:
        # Parse the local PDF file
        result = parse(pdf_path)
        if result and len(result) > 0:
            markdown_output = result[0].markdown
            chunks_output = result[0].chunks
            
            # Save markdown output to a markdown file
            with open(markdown_file, "w", encoding="utf-8") as f:
                f.write(markdown_output)
            print(f"Markdown data extracted from {pdf_name} and saved to {markdown_file}")
            
            # Save chunks to a text file as a string representation to inspect the output
            with open(chunks_file, "w", encoding="utf-8") as f:
                f.write(str(chunks_output))
            print(f"Structured chunks extracted from {pdf_name} and saved to {chunks_file}")
            
            # Also print to console for immediate feedback
            print(f"Markdown Output for {pdf_name}:")
            print(markdown_output)
            print(f"\nStructured Chunks for {pdf_name}:")
            print(chunks_output)
        else:
            print(f"No results returned for {pdf_name}")
    except Exception as e:
        print(f"Error processing {pdf_name}: {str(e)}")

# Main function to process a single PDF specified by the user
def main(pdf_name):
    print(f"Processing {pdf_name} with agentic_doc.parse...")
    process_pdf(pdf_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract data from a specified PDF using agentic_doc.parse.")
    parser.add_argument("--pdf_name", type=str, default="NCT02799602_Hussain_ARASENS_JCO'23.pdf",required=False, help="The name of the PDF file to process (e.g., NCT00268476_Clarke_SUBG_STAMPEDE_Ann Onc18.pdf)")
    args = parser.parse_args()
    main(args.pdf_name)
