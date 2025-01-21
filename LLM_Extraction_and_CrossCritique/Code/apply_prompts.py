import tiktoken
import os
import time

from prompt_design import *
from pdf_extracter.text_module import *
from pdf_extracter.image_module import *

def apply_prompts(folder, model, model_key, variables, size):

    prompts = prompt_design(variables, size) # here we get the prompts with 'size' number of variables
    print ("Number of Prompts:", len(prompts))
    filenames = os.listdir(folder) # get all filenames from the folder
    print ("Number of Files:", len(filenames)) # verify that you have extracted all the files
    print ('~'*90)
    
    image_foldername = os.getcwd() + "/PDF_Images/"
    os.makedirs(image_foldername, exist_ok=True)
    
    pdf_count = image_count = kf_count = 0
    
    # Text Extraction
    input_text = ""
    output_text = ""
    allresponses_list = []
    
    if "gpt" in model:
        chunk_start = 124000
        chunk_end = 123000
    elif "claude" in model: # token size will be adjusted according to usage tier
        chunk_start = 46000
        chunk_end = 45000
    else:
        chunk_start = 120000
        chunk_end = 110000
    
    for f in filenames:
        
        if ".pdf" in f:
            
            pdf_count += 1
            print ("\n\nFile ", f, " is in Process ...\n")
            pdffile_path = folder + f # addition of filename with folder path
            
            # text extraction from pdf
            pdftext = extract_text_from_pdf(pdffile_path) # extracting text from pdf            
            tokens_list = get_tokens(pdftext, "cl100k_base", chunk_start, chunk_end) # comment this line for previous version
            
            encoding = tiktoken.get_encoding("cl100k_base")
            tokens2 = encoding.encode(pdftext) # encode the text into tokens
            
            print ("Extracted Tokens:", len(tokens2),"\nExtracted Chunks:", len(tokens_list),"\n")
            
            allresponses = "FILENAME: "+f+"\n"
            allresponses += "TEXTRESPONSES"
            cnt = 0
            for t in tokens_list: # iterate over all the chunks of a document f
                response_text = ""
                for idx,p in enumerate(prompts): # iterate over all sub-prompts
                    cnt+=1
                    if "claude" in model:
                        response = claude_function(t, p, model_key, model)
                        response = str(response)
                        time.sleep(60) # to avoid TPM limit
                    elif "gemini" in model:
                        response = gemini_function(t,p,model_key,model)
                        #print("Here",response)
                        response = str(response)
                        if(cnt % 14 == 0):
                            time.sleep(60)
                    else:
                        response = gpt_function(t, p, model_key, model)
                        
                    response_text = response_text + "\n" + response # concatenate responces of all prompts for a single chunk of text
                    
                    input_text = input_text + "\n" + t + "\n" + p
                    output_text = output_text + "\n" + response
                    
                allresponses = allresponses + "\n" + response_text # response_text = output of one chunk
            
            # image extraction from pdf
            os.makedirs(image_foldername + f, exist_ok=True) # sub_directory to store the images of a particular pdf
            extract_images_from_pdf(pdffile_path, image_foldername + f) # function call to extract images from a pdf_file

            images = os.listdir(image_foldername + f) # get names of all images from the folder
            print ("Extracted Images:",len(images))
            allresponses = allresponses + "\n\n" + "IMAGERESPONSES"
            for img in images:

                image_count += 1 # Timer on Images for ChatGPT
                print (" - Images are in Process...")
                    
                image_path = image_foldername + f + "/" + img # get image path    
                img_response = ""
                
                for p in prompts: # iterate over all sub-prompts
                    
                    if "claude" in model:
                        image_result = image_processing_claude(p, image_path, model_key, model)
                        image_result = str(image_result)
                        if image_count % 3 == 0:
                            time.sleep(60) # to avoid TPM limit
                    elif "gpt" in model:
                        image_result = image_processing_gpt(p, image_path, model_key) # call GPT here
                        if image_count % 10 == 0:
                            time.sleep(60) # to avoid TPM limit
                    elif "gemini" in model:
                        image_result = image_processing_gemini(p,image_path,model_key)
                        image_result = str(image_result)
                        print(image_result)
                        if(image_count %14 == 0):
                            time.sleep(60)
                        
                    img_response = img_response + "\n" + image_result # concatenate responces of all prompts for a single chunk of text
                    output_text = output_text + "\n" + image_result
                    
                allresponses = allresponses + "\n" + img_response # response_text = output of one chunk
                
            allresponses_list.append(allresponses) # allresponses = output of one pdf
            
    kf_count = kf_count + (image_count*len(prompts))
    return allresponses_list, input_text, output_text, kf_count # output of all pdfs