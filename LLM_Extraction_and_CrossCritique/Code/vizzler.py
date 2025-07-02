import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

def parse_evaluation_file(file_path):
    """
    Parse an evaluation_results.txt file and return a dictionary mapping each evaluation column
    to a binary result (1 for 'Equivalent', 0 for 'Not Equivalent').
    The column name is extracted as the text before the first colon.
    """
    results = {}
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        # Skip empty lines and document markers
        if not line or (line.startswith("<") and "DOCUMENT" in line):
            continue
        
        # Process only lines that contain the evaluation marker "=>"
        if "=>" in line:
            try:
                # Extract column name using the first ":" as delimiter.
                # e.g., "Median Age (years) | Control: 64.0 vs 64.0 => Equivalent, ..."
                # will yield "Median Age (years) | Control"
                if ":" in line:
                    col_name = line.split(":", 1)[0].strip()
                else:
                    continue
                
                # Get the evaluation outcome by splitting on the "=>" delimiter.
                parts = line.split("=>")
                if len(parts) < 2:
                    continue
                outcome_part = parts[1].strip()
                outcome = outcome_part.split(",")[0].strip()
                
                # Map the outcome to a binary value: 1 for 'Equivalent', 0 for 'Not Equivalent'
                if outcome == "Equivalent":
                    result_value = 1
                elif outcome == "Not Equivalent":
                    result_value = 0
                else:
                    # Skip if outcome does not match expected values
                    continue
                    
                results[col_name] = result_value
            except Exception as e:
                print(f"Error parsing line: {line}\nError: {e}")
    return results

def collate_evaluations(root_dir):
    """
    Walk through each sub-folder in the root directory.
    Each sub-folder should be a document containing a file named evaluation_results.txt.
    Collate all evaluations into a dictionary keyed by document name.
    """
    all_results = {}
    # Each folder represents one document.
    for folder in os.listdir(root_dir):
        subfolder_path = os.path.join(root_dir, folder)
        if os.path.isdir(subfolder_path):
            file_path = os.path.join(subfolder_path, "evaluation_results_non_null_only.txt")
            if os.path.exists(file_path):
                eval_results = parse_evaluation_file(file_path)
                all_results[folder] = eval_results
            else:
                print(f"evaluation_results.txt not found in folder: {folder}")
    return all_results

def create_dataframe(results_dict):
    """
    Create a pandas DataFrame from the collated evaluations.
    Rows: evaluation fields (parsed column names)
    Columns: document names (folder names)
    Missing evaluations are represented as NaN.
    """
    # Gather all unique evaluation fields.
    all_fields = set()
    for doc, eval_dict in results_dict.items():
        all_fields.update(eval_dict.keys())
    all_fields = sorted(list(all_fields))
    
    # Sorted list of document names.
    doc_names = sorted(results_dict.keys())
    
    # Create and fill the DataFrame.
    df = pd.DataFrame(index=all_fields, columns=doc_names)
    for doc in doc_names:
        for field in all_fields:
            df.loc[field, doc] = results_dict[doc].get(field, np.nan)
    return df

def plot_heatmaps_in_chunks(df, chunk_size=40, output_folder="Plots"):
    """
    Split the DataFrame (rows corresponding to evaluation fields) into chunks of a given size,
    generate a heatmap for each chunk, and save each plot to the output folder.
    """
    # Create output folder if it doesn't exist.
    os.makedirs(output_folder, exist_ok=True)
    
    n_fields = len(df.index)
    # Determine how many chunks we'll have.
    # For instance, if there are 133 fields and chunk_size is 40,
    # then we get math.ceil(133/40)=4 chunks.
    n_chunks = (n_fields + chunk_size - 1) // chunk_size

    # Define the custom colormap: red for 0 (Not Equivalent), green for 1 (Equivalent).
    cmap = ListedColormap(["red", "green"])
    
    for i in range(n_chunks):
        start_idx = i * chunk_size
        end_idx = min(start_idx + chunk_size, n_fields)
        # Slice the DataFrame for this chunk.
        df_chunk = df.iloc[start_idx:end_idx, :]
        
        # Convert to a numeric matrix.
        matrix = df_chunk.astype(float).values
        # Mask NaN values.
        masked_matrix = np.ma.masked_invalid(matrix)
        
        # Set up the figure size; adjust as needed.
        # plt.figure(figsize=(len(df_chunk.columns) * 0.8, len(df_chunk.index) * 0.3 + 3))
        plt.figure(figsize=(8.3,11.7))
        cax = plt.imshow(masked_matrix, cmap=cmap, aspect="auto", interpolation="nearest")
        
        # Set xticks as document names and yticks as evaluation field names.
        plt.xticks(np.arange(len(df_chunk.columns)), df_chunk.columns, rotation=90)
        plt.yticks(np.arange(len(df_chunk.index)), df_chunk.index)
        plt.title(f"Evaluation Summary Heatmap (Fields {start_idx+1} to {end_idx})\n(Green: Equivalent, Red: Not Equivalent)")
        
        # Create a custom colorbar.
        norm = BoundaryNorm(boundaries=[-0.5, 0.5, 1.5], ncolors=2)
        cbar = plt.colorbar(cax, ticks=[0, 1], norm=norm)
        cbar.ax.set_yticklabels(["Not Equivalent", "Equivalent"])
        
        plt.tight_layout()
        
        # Save the plot to the output folder (naming them 1.png, 2.png, etc.)
        output_path = os.path.join(output_folder, f"{i+1}.png")
        plt.savefig(output_path)
        print(f"Plot saved to {output_path}")
        plt.close()

def main():
    # Set the root directory that contains the document folders (update this as needed).
    root_dir = "db_new_definitions"
    
    # Collate evaluations from all document folders.
    results_dict = collate_evaluations(root_dir)
    
    # Create a DataFrame from the evaluation results.
    df = create_dataframe(results_dict)
    print("Collated Evaluation Data:")
    print(df)
    
    # Plot the heatmaps in chunks and save them in the "Plots" folder.
    plot_heatmaps_in_chunks(df, chunk_size=45, output_folder="Plots")

if __name__ == "__main__":
    main()
