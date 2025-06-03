import pandas as pd

import pandas as pd

def load_definitions(csv_path="Definitions.csv", cols_to_test_path="Labels_to_Test.csv"):
    """
    Reads the Definitions.csv file and the Labels_to_Test.csv file.
    Groups columns by the 'Label' field, but only includes labels
    where 'included' is True (or 1) in Labels_to_Test.csv.
    
    Returns a dictionary where keys are labels and values are lists
    of dictionaries with keys: "Column Name" and "Definition".
    """
    # Load CSVs
    df = pd.read_csv(csv_path, encoding="utf-8")
    to_test = pd.read_csv(cols_to_test_path, encoding="utf-8")
    
    # Filter to_test where included is True (assuming 1 or True)
    included_labels = to_test[to_test['included'] == 1]['Label'].unique()

    # Group by the 'Label' column
    groups = {}
    for label, group_df in df.groupby("Label"):
        if label in included_labels:
            groups[label] = group_df[["Column Name", "Definition"]].to_dict(orient="records")
        
    return groups


if __name__ == "__main__":
    definitions = load_definitions("Definitions.csv")
    print(definitions)
