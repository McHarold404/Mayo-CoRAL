def prompt_design(variables, size):

    splits = int(len(variables)/size) # division of variables into chunks for each prompt
    start = 0
    end = size
    list_of_queries = []

    # for each query, we first define the variables from start_point to end_point (first loop), and then append these variables in the prompt (second loop)
    for i in range(splits+1):
        # first case (i = 0): start = 0, end = size
        if i < splits and i > 0: # intermediate cases (except for the first and last ones)
            start = end
            end = end + size
        elif i == splits and len(variables) % size != 0: # last case
            start = end
            end = len(variables)
            
        elif i>0: # this is the special case, when % = 0 and i > 0
            break        
        
        query = """Extract from the given text, Extract """
        for j in range(start, end): # append variables from start to end in the prompt
            if j==start:
                query += "[" + variables[j] + "]"
            else:
                query += ", " + "[" + variables[j] + "]"
        query += """. Where the information is not available, the output should be “NA”. 
        Do not include information outside the given text. 
        Generate short and precise responses. 
        Also, for every value you extract, give the exact citations from the document to where it is present 
        The citaion should include the exact sentence from the document from where the value was extracted or inferred and where that sentence is present in the document,. """
        list_of_queries.append(query.strip('\n')) # list of all prompts

    return list_of_queries