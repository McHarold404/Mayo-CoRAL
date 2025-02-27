import fitz
import numpy
import pandas
import base64
import requests
import anthropic
import openai
import base64
from dotenv import dotenv_values
from dotenv import load_dotenv
import os
import PIL.Image
import google.generativeai as genai


# save the complete page that contains images/tables as an image
def extract_images_from_pdf(pdf_path, image_folder): 
    
    keywords = ["Table", "Figure", "TABLE", "FIGURE", "table", "figure"]
    dpi = 500
    doc = fitz.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()

        # Check if any of the keywords exist in the current page's text
        if any(keyword in text for keyword in keywords):
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
            image_filename = f"{image_folder}/page_{page_num + 1}_high_res.png"
            pix.save(image_filename)
    
    doc.close()
    
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8') # image is decoded into a sutiable format

# This function is used to process image using GPT.
def image_processing_gpt(query, image_path, gpt_key):
    
    base64_image = encode_image(image_path) # image format conversion
    
    # setting of API
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {gpt_key}"
    }
    
    # here we load query and image 
    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
          {
            "role": "user",
            "content": [
              {
                "type": "text",
                "text": query
              },
              {
                "type": "image_url",
                "image_url": {
                  "url": f"data:image/jpeg;base64,{base64_image}"
                }
              }
            ]
          }
        ],
        "max_tokens": 1000
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload) # API call
    response = response.text
    if "content" in response and len(response) > 50:
        response = response.split("content")[1][4:] # start from 4th char till 42nd last char
    if "finish_reason" in response and len(response) > 50:
        response = response.split("finish_reason")[0][:-17] # start from 4th char till 42nd last char

    return response

# This function is used to process image using Claude.
def image_processing_claude(query, image_path, claude_key, model_name):
    
    base64_image = encode_image(image_path) # image format conversion
    
    client = anthropic.Anthropic(
        api_key = claude_key,
    )
        
    message = client.messages.create(
        model = model_name,
        max_tokens = 1024,
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": base64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": query
                    }
                ],
            }
        ],
    )
    return str(message.content)


# This function is used to process images using Gemini 1.5 Flash.


# Function to encode the image to base64
def encode_image(image_path):
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# This function is used to process images using Gemini 1.5 Flash
def image_processing_gemini(query, image_path, model_key):
    
    # Initialize the Gemini model
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
    
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    genai.configure(api_key=model_key)   
    # Convert the image to base64
    #base64_image = encode_image(image_path)

    # Upload the image file to Gemini using the File API

    #uploaded_file = model.upload_file(media=base64_image)
    uploaded_file = PIL.Image.open(image_path)
    # Check if file upload was successful
    if not uploaded_file:
        return "Error: Image upload failed."
    
    # Prepare the prompt with the query and the uploaded image
    response = model.generate_content([query, uploaded_file])

    # Check if a response was returned
    if response and hasattr(response, 'text'):
        return response.text
    else:
        return "No valid response received from Gemini."


# load_dotenv()
# api_key = os.getenv("GEMINI_KEY")
# #print("got till here")
 
# print(image_processing_gemini(query="describe this image",model_key=api_key,image_path='/Users/naman/Desktop/ASU/Mayo Clinic/LLMs_ExtractionWithCrossCritique-main/LLM_Extraction_and_CrossCritique/Code/PDF_Images/NCT02446405_Sweeney_ENZAMET_Lancet Onc23.pdf/page_2_high_res.png'))