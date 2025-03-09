import torch
from transformers import AutoProcessor, TableTransformerForObjectDetection
from PIL import Image

# Define the model name
model_name = "microsoft/table-transformer-structure-recognition"

# Load the processor and model
processor = AutoProcessor.from_pretrained(model_name)
model = TableTransformerForObjectDetection.from_pretrained(model_name)

# Load your table image (replace with your actual image file path)
image_path = "/Users/naman/Desktop/ASU/Mayo Clinic/table1.jpeg"
image = Image.open(image_path).convert("RGB")

# Preprocess the image: the processor prepares the image for the model
inputs = processor(images=image, return_tensors="pt")

# Run the model inference
with torch.no_grad():
    outputs = model(**inputs)

print("Model Outputs:" + str(outputs))
# ------------------------------------------------------------------------------
# Post-processing: Convert model outputs into a Markdown representation
#
# The model outputs (e.g. predicted bounding boxes and logits) contain information 
# about the detected table structure. You will need to parse these outputs and convert 
# them into a Markdown table format.
#
# In some implementations, the processor may offer a helper function (e.g. 
# `processor.post_process_table(...)`) to do this automatically.
#
# Below, we attempt to use such a method; if it does not exist, you'll need to implement 
# your own logic to:
#   1. Determine the grid layout (rows and columns) from the bounding boxes.
#   2. Extract cell contents (if available) or simply build an empty table.
#   3. Format the table into Markdown.
# ------------------------------------------------------------------------------

try:
    # Attempt to use a built-in post-processing helper (if available)
    table_markdown = processor.post_process_table(outputs, image.size)
except AttributeError:
    # Fallback: a simple custom post-processing example (this is a placeholder)
    # For demonstration, we assume a table with 3 columns and 4 rows.
    # In practice, you need to parse outputs.pred_boxes (and possibly logits) to infer
    # the actual table structure.
    n_cols, n_rows = 3, 4
    # Build a simple empty Markdown table as an example:
    header = "| " + " | ".join(["Header"] * n_cols) + " |"
    separator = "| " + " | ".join(["---"] * n_cols) + " |"
    rows = [header, separator]
    for i in range(n_rows):
        row = "| " + " | ".join([f"Cell {i+1}-{j+1}" for j in range(n_cols)]) + " |"
        rows.append(row)
    table_markdown = "\n".join(rows)

# Output the Markdown representation of the table
print("Extracted Table in Markdown Format:")
print(table_markdown)
