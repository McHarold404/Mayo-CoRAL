import os
import google.generativeai as genai
import time 
import json
from dotenv import load_dotenv

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

def ask_gemini(text : str, prompt_path : str =None, key = 1,model_name = "gemini-1.5-flash"):
    
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
        return response.text

    except Exception as e:
        return f"An error occurred: {str(e)}"