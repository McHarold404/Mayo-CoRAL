import pandas as pd

def load_definitions(csv_path="Definitions.csv"):
    """
    Reads the Definitions.csv file using pandas and groups columns by the 'Label' field.
    Returns a dictionary where keys are labels and values are lists of dictionaries,
    each with keys: "Column Name" and "Definition".
    """
    # Load CSV into a DataFrame
    df = pd.read_csv(csv_path, encoding="utf-8")
    
    # Group by the 'Label' column
    groups = {}
    for label, group_df in df.groupby("Label"): # change "Column Name" to "Label" to group columns and run them.
        # Convert the group DataFrame to a list of dicts containing only the "Column Name" and "Definition"
        groups[label] = group_df[["Column Name", "Definition"]].to_dict(orient="records")
        
    return groups

if __name__ == "__main__":
    definitions = load_definitions("Definitions.csv")
    print(definitions)
