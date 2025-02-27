import pandas as pd
from openpyxl import load_workbook

# Define file path
file_path = "var_definitions.xlsx"

# Load existing Excel file
with pd.ExcelWriter(file_path, engine="openpyxl", mode="a") as writer:
    # Create a new DataFrame (example data)
    new_data = pd.DataFrame({"Column1": [1, 2, 3], "Column2": ["A", "B", "C"]})

    # Write DataFrame to a new sheet named "NewSheet"
    new_data.to_excel(writer, sheet_name="NewSheet", index=False)

print("New sheet added successfully!")
