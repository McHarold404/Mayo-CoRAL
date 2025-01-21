import numpy as np
import pandas as pd


from file_utils import *
from apply_prompts import *
from cost_calculator import *
from post_processing import *


def extract_using_llms(model, model_key, prompt_size, pdf_folder_path, variable_file_path):
    
    df = pd.read_excel(variable_file_path,sheet_name='Definitions')
    variables = []
    for x,y,z in zip(df['Column Name'],df['Definition'],df['Procedure']):
        variables.append(x+":"+ y + "How to extract:" + z)
    #variables = list(dd.loc[0])
    
    pdf_folder_path = pdf_folder_path + "/"
                    
    print ('~'*90)
    print ("LLMs are in Process to Generate Responses")
    print ("Model:", model, "\t Prompt Size:", prompt_size, "\t# of Variables:", len(variables))
    print ('~'*90)

    results, input_text, output_text, kf_count = apply_prompts(pdf_folder_path, model, model_key, variables, prompt_size)

    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)

    output_path = os.getcwd()
    write_path = output_path + "/" + model + "__" + current_time + ".txt"
    write_raw_responses(results, write_path)
    print ("\nRaw Responses are Recorded in File:", write_path)
    
    print ("\n\nPost Processed Results\n")
    pp_resp = post_processing(write_path, model_key, model)

    input_text += str(results)
    output_text += str(pp_resp)

    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)
    write_path = output_path + "/" + model + "_PP" + "__" + current_time + ".txt"
    write_raw_responses(pp_resp, write_path)
    print ("\nPost Processed Responses are Recorded in File:", write_path)

    
    cost = cost_calculation(input_text, output_text, kf_count, 0.005, 0.015)
    print ("\nTotal Cost of GPT-04:", cost)
    #else:
    #    cost = cost_calculation(input_text, output_text, kf_count, 0.005, 0.015)
    #    print ("\nTotal Cost of Claude:", cost)

def extract_from_files(raw_resp_path, pp_resp_path):

    print ("Reading Recorded Raw Responses")
    results = read_raw_responses(raw_resp_path)

    for res in results:
        print (res,"\n")

    print ("Reading Recorded Post-Processed Responses")
    results = read_raw_responses(pp_resp_path)

    for res in results:
        toks = res.split("\n")
        for tok in toks:
            print (tok)