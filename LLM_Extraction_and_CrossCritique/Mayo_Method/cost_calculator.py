import tiktoken
import numpy as np


def cost_calculation(input_text, output_text, kf_count, input_cost, output_cost):
    
    encoding = tiktoken.get_encoding("cl100k_base")
    
    #input cost estimation
    if (len(input_text)) > 1:
        tokens = encoding.encode(input_text) # encode the text into tokens
        print ("Input Tokens:",len(tokens))
        chunks = int(len(tokens)/1000) + 1
        input_cost = input_cost * chunks
    else:
        input_cost = 0

    #output cost estimation
    if (len(output_text)) > 1:
        tokens = encoding.encode(output_text) # encode the text into tokens
        print ("Output Tokens:",len(tokens))
        chunks = int(len(tokens)/1000) + 1
        output_cost = output_cost * chunks
    else:
        output_cost = 0
        
    #Image cost estimation
    image_cost = 0
    if kf_count > 0:
        print ("Images:",kf_count)
        image_cost = kf_count * 0.0025
    
    total_cost = input_cost + output_cost + image_cost
    return  total_cost