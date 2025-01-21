
import pandas as pd

def parse_file_to_dataframe(file_path):
    """
    Reads a file and converts it into a pandas DataFrame where each column is the first word
    of each line and the values are the text following the '::' separator.
    
    Args:
    - file_path (str): The path to the input file.
    
    Returns:
    - pd.DataFrame: The resulting DataFrame.
    """
    data = dict()    
    with open(file_path, 'r') as f:
        for line in f.readlines():
            # Remove leading/trailing whitespace
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Skip lines without '::'
            if '::' not in line:
                continue
            # Split the line into key and value
            key, value = line.split('::', 1)
            #print(f"Key:{key}",f"Value:{value}")
            key = key.strip()
            value = value.strip()
            # Get the first word from the key
            # Append the value to the corresponding list in the dictionary
            data[key]=(value)
    
 
    # Create DataFrame from the dictionary
    #print(data)
    df = pd.DataFrame(data,index=[0])
    return df


from difflib import SequenceMatcher

def similarity(item1: str, item2: str):
    return SequenceMatcher(None, str(item1), str(item2)).ratio()



def evaluate_similarity_from_excel(file_path1, file_path2, threshold=0.9):
    """
    Reads two Excel files, extracts rows with matching 'Trial Name' values, and evaluates similarity
    between corresponding elements in selected columns for each matching row.
    
    Parameters:
    - file_path1, file_path2: Paths to the Excel files
    - threshold: Similarity threshold, default is 0.9 (90%)

    Returns:
    - A list of tuples containing the trial name, corresponding elements from each list,
      and their similarity score, only for those with similarity less than the threshold.
    """
    # Load the Excel sheets into dataframes
    df1 = parse_file_to_dataframe(file_path1)
    df2 = pd.read_excel(file_path2)

    # Find common 'Trial Name' values in both files
    common_trials = set(df1['Trial Name']).intersection(df2['Trial Name'])

    # Store results for pairs with similarity below the threshold
    low_similarity_results = []

    # Loop through each common trial name
    for trial in common_trials:
        # Extract rows for the current trial name
        row1 = df1[df1['Trial Name'] == trial].iloc[0]
        row2 = df2[df2['Trial Name'] == trial].iloc[0]

        # Convert the rows (excluding the 'Trial Name' column) to lists for comparison
        list1 = row1.drop('Trial Name').tolist()
        list2 = row2.drop('Trial Name').tolist()
        cols_1 = df1.columns.to_list()
        cols_2 = df2.columns.to_list()
        #assert(cols_1 == cols_2)
        # Evaluate similarity between each pair of corresponding elements
        for col, item1, item2 in zip(cols_1,list1, list2):
            similarity_score = similarity(item1,item2)
            if similarity_score < threshold:
                low_similarity_results.append((col, item1, item2, similarity_score))

    return low_similarity_results



print(parse_file_to_dataframe('/Users/naman/Desktop/ASU/Mayo Clinic/LLMs_ExtractionWithCrossCritique-main/LLM_Extraction_and_CrossCritique/Code/gemini-1.5-flash_PP__15:31:22.txt').columns)

low_similarity_results = evaluate_similarity_from_excel("gemini-1.5-flash_PP__15:31:22.txt", "Gold_Labels.xlsx")
for trial, item1, item2, score in low_similarity_results:
    print(f"Trial: '{trial}', Pair: '{item1}' - '{item2}', Similarity Score: {score*100:.2f}%")