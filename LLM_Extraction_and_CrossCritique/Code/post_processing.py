from file_utils import *
from pdf_extracter.text_module import *
from pdf_extracter.image_module import *

def post_processing(path, model_key, model):
    
    results = read_raw_responses(path) # read the raw_response from the file
    
    pp_query = """As an expert in processing the text in a structured format, identify:
    1.Name of the clinical trial
    2.Names of variables (keep the variable name short and consistent)
    3.Value of each variable
    4.Exact citation in the document fromw where the variable was extracted
    Present the outcome as:
    Example OUTPUT (tabular format):
    Variable 1 name :: Variable value :: Citation from the document
    Variable 2 name :: Variable value :: Citation from the document.
    4. Generate the output as concise as possible for all variables. Also include the variables for which value is NA.
    5. Do not include any other information including extra spaces, numbering and special character."""
    
    pp_resps = []
    for result in results:
        if "gpt" in model:
            pp_resp = gpt_function(result, pp_query, model_key, model)
        elif "gemini"in model:
            pp_resp = gemini_function(result,pp_query,model_key,model)
            pp_resp = str(pp_resp)
        else:
            pp_resp = claude_function(result, pp_query, model_key, model)
            pp_resp = str(pp_resp)
        pp_resps.append(pp_resp)
        print (pp_resp,"\n")
            
    return pp_resps


import fuzzywuzzy
from fuzzywuzzy import fuzz

def verify_responses(responses_path=None, document_path=None, threshold=80):
    # Read the responses file
    with open(responses_path, 'r') as out:
        lines = out.readlines()
    
    # Parse the responses into a list of tuples (var, value, ref)
    responses = []
    for line in lines:
        # Split using "::" and ensure the split results in exactly 3 parts
        parts = line.strip().split("::")
        if len(parts) == 3:
            responses.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
    
    # Extract text content from the PDF document
    document_content = extract_text_from_pdf(document_path)
    
    # List to store unverified responses
    unverified_responses = []
    
    # Check for fuzzy string matching between ref and document content
    for var, value, ref in responses:
        if ref:  # Ensure ref is not empty
            # Perform fuzzy matching between ref and the document content
            match_score = fuzz.partial_ratio(ref, document_content)
            
            # If the reference is not similar enough, add it to the unverified list
            if match_score < threshold:
                unverified_responses.append((var, value, ref,match_score))
        else:
            # If ref is missing, consider it unverified
            unverified_responses.append((var, value, ref))
    
    return unverified_responses

