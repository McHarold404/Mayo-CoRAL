import fitz
import numpy as np
import pandas
import base64
import requests
import tiktoken
import anthropic
import openai 
from openai import OpenAI
from dotenv import dotenv_values
import google.generativeai as genai



def extract_text_from_pdf(pdf_path): # This function will accept the .pdf file path
    
    pdf_document = fitz.open(pdf_path) # open the file using fitz library
    extracted_text = "" # extracted text will be added to this storage variable
    
    # Iterate over each page
    # pdf_document.page_count is a built-in function that count the number of pages
    for page_number in range(pdf_document.page_count):
        page = pdf_document[page_number] # Here, we can object named page
        page_text = page.get_text() # Here, the text has been extracted from the page
        # Append the text to the overall extracted_text string
        extracted_text += page_text # += means append mode
        
    print ("Original Text:",len(extracted_text))
    
    # Exclude the irrelevant sections
    
    last_section_start = -1
    last_section_start = extracted_text.find("REFERENCES\n")
    if last_section_start == -1:
        last_section_start = extracted_text.find("References\n")
    if last_section_start == -1:
        last_section_start = extracted_text.find("References \n")
    if last_section_start != -1:
        extracted_text = extracted_text[:last_section_start].strip()
    
    last_section_start = -1
    last_section_start = extracted_text.find("ORCID\n")
    if last_section_start != -1:
        temp_text = extracted_text[last_section_start:-1]
        table_check = temp_text.find("TABLE")
        if table_check == -1:
            extracted_text = extracted_text[:last_section_start].strip()
        else:
            table_check = -1
    
    last_section_start = -1
    last_section_start = extracted_text.find("Acknowledgements\n")
    if last_section_start == -1:
        last_section_start = extracted_text.find("ACKNOWLEDGEMENTS\n")
    if last_section_start != -1:
        temp_text = extracted_text[last_section_start:-1]
        table_check = temp_text.find("TABLE")
        if table_check == -1:
            extracted_text = extracted_text[:last_section_start].strip()
        else:
            table_check = -1
        
    last_section_start = -1
    last_section_start = extracted_text.find("Appendix\n")
    if last_section_start == -1:
        last_section_start = extracted_text.find("APPENDIX\n")
    if last_section_start != -1:
        temp_text = extracted_text[last_section_start:-1]
        table_check = temp_text.find("TABLE")
        if table_check == -1:
            extracted_text = extracted_text[:last_section_start].strip()
        else:
            table_check = -1        
    
    last_section_start = -1
    last_section_start = extracted_text.find("Contributors\n")
    if last_section_start == -1:
        last_section_start = extracted_text.find("AUTHOR CONTRIBUTIONS\n")
    if last_section_start == -1:
        last_section_start = extracted_text.find("AUTHOR CONTRIBUTION\n")
    if last_section_start != -1:
        temp_text = extracted_text[last_section_start:-1]
        table_check = temp_text.find("TABLE")
        if table_check == -1:
            extracted_text = extracted_text[:last_section_start].strip()
        else:
            table_check = -1
    
    last_section_start = -1
    last_section_start = extracted_text.find("AFFILIATIONS\n")
    if last_section_start == -1:
        last_section_start = extracted_text.find("Affiliations\n")
    if last_section_start != -1:
        temp_text = extracted_text[last_section_start:-1]
        table_check = temp_text.find("TABLE")
        if table_check == -1:
            extracted_text = extracted_text[:last_section_start].strip()
        else:
            table_check = -1
    
    last_section_start = -1
    last_section_start = extracted_text.find("Declaration of interests\n")
    if last_section_start == -1:
        last_section_start = extracted_text.find("DECLARATION OF INTERESTS\n")
    if last_section_start != -1:
        temp_text = extracted_text[last_section_start:-1]
        table_check = temp_text.find("TABLE")
        if table_check == -1:
            extracted_text = extracted_text[:last_section_start].strip()
        else:
            table_check = -1
    
    print ("Extracted Text:",len(extracted_text))

    # Close the PDF file
    pdf_document.close() # we need to close the document to avoid file system errors
    return extracted_text

def get_tokens(string: str, encoding_name: str, ch_start, ch_end) -> int:
    
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(string) # encode the text into tokens
    tokens_str = [encoding.decode_single_token_bytes(token) for token in tokens]
    chunks = [list(np.arange(a, a + ch_start)) for a in range(0, len(tokens_str), ch_end)]
    
    list_of_strings = []
    for c in range(len(chunks)):
        start = chunks[c][0]
        end = chunks[c][-1]
        mystring = encoding.decode(tokens[start: end]) # decode to form string for each chunk
        list_of_strings.append(mystring) # text/strings of all chunks is mapped in the list
        
    return list_of_strings

# Processing of Text by GPT
def gpt_function(t, p, gpt_key, model_name):
    
    openai.api_key = gpt_key
    client = OpenAI(
        api_key = gpt_key,
    )
    
    chat_completion = client.chat.completions.create(
            messages=[
                { "role": "system", "content": "You are an expert of data extraction from a given chunk of text."}, # system_role
                { "role": "user", "content": t+"\n"+p}, # t = text, p = prompt
            ],
            extra_headers={'Authorization': f'Bearer {openai.api_key}'},
            model=model_name,
            temperature=0.00000000001,
#         max_tokens=150,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
    )
    response = chat_completion.choices[0].message.content # response from a single chunk for a single prompt
    return response

# Processing of Text by Claude
def claude_function(t, p, claude_key, model_name):
    
    client = anthropic.Anthropic(
        api_key = claude_key,
    )
    
    message = client.messages.create(
        model = model_name,
        max_tokens = 1000,
        temperature = 0.0,
        system = "You are an expert of data extraction from a given chunk of text.",
        messages = [
            {"role": "user", "content": t+"\n"+p}
    ])
    
    msg = message.content
    return msg

# Processing of Text by Gemini
def gemini_function(text,prompt, model_key, model_name="gemini-1.5-flash"):
    
    # Set up the API client for Gemini
    safety_settings = [
            {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE"
        },
            {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE"
        },
            {
            "category": "HARM_CATEGORY_HARASSMENT", 
            "threshold": "BLOCK_NONE"
        },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
        }
    ]

    model = genai.GenerativeModel(model_name=model_name)
    genai.configure(api_key=model_key)
    chat = model.start_chat(history=[])
    response = chat.send_message([text + "\n" + prompt],safety_settings=safety_settings)
    # Call the Gemini API to generate content based on the provided text and prompt
    #response = model.generate_content(, api_key=model_key)

    # Extract and return the text content from the API response
    if hasattr(response, 'text'):
        return response.text
    else:
        return "Error: No valid text response received."
