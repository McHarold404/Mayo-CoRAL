import os
import google.generativeai as genai
import time 
import json
from dotenv import load_dotenv
from token_tracker import add_tokens

def ask_gemini(text : str, prompt_path : str =None, key = 2,model_name = "gemini-2.0-flash"):
    
    # Import necessary module for GenerativeModel if not already done
    load_dotenv()
    if key == 1:
        api_key = os.getenv("GEMINI_KEY")
    elif key == 2:
        api_key = os.getenv("GEMINI_KEY_2")
    elif key == 3:
        api_key = os.getenv("GEMINI_KEY_3")
    elif key == 4:
        api_key = os.getenv("GEMINI_KEY_4")
    elif key == 5:
        api_key = os.getenv("GEMINI_KEY_5")
    elif key == 6:
        api_key = os.getenv("GEMINI_KEY_6")
    else:
        raise ValueError("No key specified")
    # Check if a prompt path is provided and read prompt text
    if prompt_path and text:
        with open(prompt_path, 'r') as file:
            prompt = file.read().strip()
    else:
        return "Error: no data given"

    # Initialize the GenerativeModel with the required configuration
    generation_config = {
        "temperature": 0.1,
        "top_p": 0.1,
        "top_k": 20,
        "response_mime_type": "text/plain",
    }
    genai.configure(api_key=api_key)
    try:
        # Instantiate the model
        model = genai.GenerativeModel(
            model_name=model_name,  # replace with actual model name
            # The `generation_config` dictionary in the GeminiBot class and the ask_gemini function is
            # used to configure the generation settings for the GenerativeModel. It contains the
            # following key-value pairs:
            generation_config=generation_config,
            system_instruction= prompt
        )
        
        # Start a chat session
        chat_session = model.start_chat(history=[])
        # Get the response by sending the prompt
        response = chat_session.send_message(text)
        if response.usage_metadata:
            add_tokens(response.usage_metadata.prompt_token_count,response.usage_metadata.candidates_token_count)

        return response.text


    except Exception as e:
        return f"An error occurred: {str(e)}"
    
    
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image

# def ask_gemini_with_image(image, prompt_path: str, key=2, model_name="gemini-2.0-flash"):
#     """
#     Sends a single image to the Gemini model for processing, using a system prompt from a file.

#     Args:
#         image: An image file path or a PIL Image object.
#         prompt_path: Path to a file containing the system prompt.
#         key: Integer specifying which API key to use (1-6).
#         model_name: The name of the Gemini model to use (defaults to "gemini-pro-vision").

#     Returns:
#         The text response from the Gemini model, or an error message.
#     """
#     from dotenv import load_dotenv
#     import os
#     import PIL.Image
#     import google.generativeai as genai

#     load_dotenv()
#     if key == 1:
#         api_key = os.getenv("GEMINI_KEY")
#     elif key == 2:
#         api_key = os.getenv("GEMINI_KEY_2")
#     elif key == 3:
#         api_key = os.getenv("GEMINI_KEY_3")
#     elif key == 4:
#         api_key = os.getenv("GEMINI_KEY_4")
#     elif key == 5:
#         api_key = os.getenv("GEMINI_KEY_5")
#     elif key == 6:
#         api_key = os.getenv("GEMINI_KEY_6")
#     else:
#         raise ValueError("No key specified")

#     if not prompt_path:
#         return "Error: No prompt path provided."

#     try:
#         with open(prompt_path, 'r') as file:
#             prompt = file.read().strip()
#     except FileNotFoundError:
#         return f"Error: Prompt file not found: {prompt_path}"
#     except Exception as e:
#         return f"Error reading prompt file: {e}"

#     # Configure Gemini with the API key.
#     genai.configure(api_key=api_key)
#     model = genai.GenerativeModel(model_name=model_name)

#     # Process the image: if it's a file path, open it; if it's already a PIL Image, use it directly.
#     try:
#         if isinstance(image, str):
#             processed_image = PIL.Image.open(image)
#         elif isinstance(image, PIL.Image.Image):
#             processed_image = image
#         else:
#             return "Error: Image must be a file path or a PIL Image object."
#     except Exception as e:
#         return f"Error processing image: {e}"

#     # Call the Gemini model with the prompt and the image directly.
#     try:
#         response = model.generate_content([prompt, processed_image])
#         if response and hasattr(response, 'text'):
#             if response.usage_metadata:
#                 add_tokens(response.usage_metadata.prompt_token_count,response.usage_metadata.candidates_token_count)
#             return response.text
       
#         else:
#             return "No valid response received from Gemini."
#     except Exception as e:
#         return f"Error: {e}"
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image

def ask_gemini_with_image(images, prompt_path: str, user_prompt_text: str = "", key=2, model_name="gemini-2.0-flash"):
    """
    Sends one or more images to the Gemini model for processing, using a system prompt from a file and an optional user prompt text.

    Args:
        images: A PIL Image object or a list of PIL Image objects.
        prompt_path: Path to a file containing the system prompt.
        user_prompt_text: Additional free text to be combined with the system prompt (optional).
        key: Integer specifying which API key to use (1-6).
        model_name: The name of the Gemini model to use (defaults to "gemini-2.0-flash").

    Returns:
        The text response from the Gemini model, or an error message.
    """

    load_dotenv()
    api_keys = {
        1: os.getenv("GEMINI_KEY"),
        2: os.getenv("GEMINI_KEY_2"),
        3: os.getenv("GEMINI_KEY_3"),
        4: os.getenv("GEMINI_KEY_4"),
        5: os.getenv("GEMINI_KEY_5"),
        6: os.getenv("GEMINI_KEY_6"),
    }
    api_key = api_keys.get(key)
    if not api_key:
        return "❌ Error: Invalid or missing API key."

    if not prompt_path:
        return "❌ Error: No prompt path provided."

    try:
        with open(prompt_path, 'r') as file:
            prompt = file.read().strip()
    except FileNotFoundError:
        return f"❌ Error: Prompt file not found: {prompt_path}"
    except Exception as e:
        return f"❌ Error reading prompt file: {e}"

    # Combine system prompt with user prompt text if provided
    final_prompt = prompt
    if user_prompt_text:
        final_prompt += "\n\nUser Input:\n" + user_prompt_text

    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=model_name)

    # Normalize image input
    if not isinstance(images, list):
        images = [images]

    # Validate all images
    processed_images = []
    try:
        for img in images:
            if isinstance(img, str):
                processed_images.append(Image.open(img).convert("RGB"))
            elif isinstance(img, Image.Image):
                processed_images.append(img.convert("RGB"))
            else:
                return "❌ Error: Each image must be a file path or a PIL.Image.Image object."
    except Exception as e:
        return f"❌ Error processing images: {e}"

    # Send prompt + all images to Gemini
    try:
        response = model.generate_content([final_prompt] + processed_images)

        if response and hasattr(response, 'text'):
            if response.usage_metadata:
                add_tokens(
                    response.usage_metadata.prompt_token_count,
                    response.usage_metadata.candidates_token_count
                )
            return response.text
        else:
            return "⚠️ No valid response received from Gemini."
    except Exception as e:
        return f"❌ Error from Gemini: {e}"
