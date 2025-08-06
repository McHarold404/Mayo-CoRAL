import os
import google.generativeai as genai
import time 
import json
from dotenv import load_dotenv
from token_tracker import add_tokens

class GeminiBot:
    def __init__(self, api_key=None, model_name="gemini-1.5-flash", 
                 data_path=None, prompt_path=None,meta_data = None,limit_rows = None, output_path = None):
        #load_dotenv()
        self.api_key = api_key 
        if not self.api_key:
            raise ValueError("API key is required. Set it in the constructor or as an environment variable 'GOOGLE_AI_API_KEY'")
        genai.configure(api_key=self.api_key)
        self.limit_rows = limit_rows
        self.output_path = output_path
        self.meta_data = meta_data
        self.model_name = model_name
        self.data_path = data_path
        self.prompt_path = prompt_path
        self.generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        self.model = self._create_model()
        self.chat_session = self.model.start_chat(history=[])

    def _create_model(self):
        return genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
        )

    def get_response(self, user_message):
        try:
            response = self.chat_session.send_message(user_message)
            if response.usage_metadata:
                global total_token_usage
                total_token_usage += response.usage_metadata.total_token_count
            return response.text
        except Exception as e:
            return f"An error occurred: {str(e)}"

    def load_prompt(self):
        try:
            with open(self.prompt_path, 'r') as file:
                return file.read().strip()
        except FileNotFoundError:
            print(f"Prompt file not found at {self.prompt_path}")
            return ""
        except Exception as e:
            print(f"Error reading prompt file: {str(e)}")
            return ""

    def load_data(self):
        try:
            with open(self.data_path, 'r') as file:
                return [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            print(f"Data file not found at {self.data_path}")
            return []
        except Exception as e:
            print(f"Error reading data file: {str(e)}")
            return []
    
    def load_meta_data(self):
        if self.meta_data is None:
            print(f"Error reading meta data, file not found")
            return []
        try:
            with open(self.meta_data,"r") as json_file:
                meta = json.load(json_file)
            return [x['response'] for x in meta]
        
        except Exception as e:
            print(f"Error reading data file: {str(e)}")
            return []
            
    def run_inference(self):
        print("Starting inference")
        data = self.load_data()
        prompt = self.load_prompt()
        meta = self.load_meta_data()

        if not data:
            print("No data to process. Exiting.")
            return
        
        if not prompt:
            print("No prompt loaded. Exiting.")
            return

        results = []
        for i, point in enumerate(data, 1):
            if(i%15 == 14):
                time.sleep(60)
            if( self.limit_rows is not None and i > self.limit_rows):
                break
            if len(meta) == 0:
                message = f"{prompt}:\n{point}"
            else:
                message = f"{prompt}:\n {meta[i-1]}:\n{point}"
            response = self.get_response(message)
            results.append({'data_point': i,'input': point,'response': response})
            print(f"Data point {i}:")
            # print(f"Data point {i}:")
            #print(f"Input: {message}")
            # print("0----0")
            # print(f"AI Response: {response}")
            # print("-" * 50)
            
            #results.append((point, response))
        with open(self.output_path,"w") as json_file:
            json.dump(results,json_file,indent=2)
        return results

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

def ask_gemini_with_image(images, prompt_path: str, key=2, model_name="gemini-2.0-flash"):
    """
    Sends one or more images to the Gemini model for processing, using a system prompt from a file.

    Args:
        images: A PIL Image object or a list of PIL Image objects.
        prompt_path: Path to a file containing the system prompt.
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
        with open(prompt_path, encoding="utf-8") as file:
            prompt = file.read().strip()
    except FileNotFoundError:
        return f"❌ Error: Prompt file not found: {prompt_path}"
    except Exception as e:
        return f"❌ Error reading prompt file: {e}"

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
        response = model.generate_content([prompt] + processed_images)

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
