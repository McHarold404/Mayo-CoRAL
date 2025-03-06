import os
from openai import OpenAI
import json

client = OpenAI(api_key="")
from dotenv import load_dotenv

class GPT4MiniBot:
    def __init__(self, api_key=None, model="gpt-4o-mini", 
                 data_path=None, prompt_path=None, output_path = None, meta_data = None,limit_rows = None):
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required. Set it in the constructor or as an environment variable 'OPENAI_API_KEY'")
        self.model = model
        self.limit_rows = limit_rows
        self.output_path = output_path
        self.meta_data = meta_data
        self.data_path = data_path
        self.prompt_path = prompt_path

    def get_api_response(self, message):
        try:
            response = client.chat.completions.create(model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": message}
            ])
            return response.choices[0].message.content
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
            if( self.limit_rows is not None and i > self.limit_rows):
                break
            
            if len(meta) == 0:
                message = f"{prompt}:\n{point}"
            else:
                message = f"{prompt}:\n {meta[i-1]}:\n{point}"
            
            final_input = message
            response = self.get_api_response(final_input)
            results.append({'data_point': i,'input': point,'response': response})
            print(f"Data point {i}:")
            #print(f"Input: {point}")
            #print(f"AI Response: {response}")
            #print("-" * 50)
        print("saving outputs")
        try:
            with open(self.output_path,"w") as json_file:
                json.dump(results,json_file,indent=2)
        except Exception as e:
            print("Error occured")

        return results

if __name__ == "__main__":
    bot = GPT4MiniBot(
        data_path="path/to/your/data.txt",
        prompt_path="path/to/your/prompt.txt"
    )
    bot.run_inference()


def ask_chatgpt(text: str, prompt_path=None,temperature = 0.1,model_name = "gpt-4o"):
    # Check if a prompt path is provided and read prompt text
    load_dotenv()
    api_key =os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key = api_key)
    if prompt_path and text:
        with open(prompt_path, 'r') as file:
            prompt = file.read().strip()
    else:
        return "Error: no data given"

    # Model configuration - replace 'gpt-4' with the specific model if needed
    #input = text + prompt
    # Send the prompt to the model
    response = client.chat.completions.create(
    model=model_name,
    messages=[
        {'role' : "system" , "content" : prompt},
        {'role': "user" , "content": text}
    ],
    temperature=temperature,
    #top_p=0.1
    )
        
    # Return the response content
    return response.choices[0].message.content

import os
from dotenv import load_dotenv
import openai

def ask_chatgpt_inline(prompt: str, text: str, temperature=0.1, top_p=1.0, model_name="gpt-4o"):
    """
    Send the prompt and text directly as variables to ChatGPT.
    
    Parameters:
        prompt (str): The system prompt text.
        text (str): The user's input text.
        temperature (float): Sampling temperature.
        top_p (float): Nucleus sampling probability threshold.
        top_k (Optional[int]): Not supported by the OpenAI Chat API; provided for interface consistency.
        model_name (str): The model to use.
        
    Returns:
        str: The response content from ChatGPT.
    """
    load_dotenv()  # Load environment variables from a .env file, if available.
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "Error: OPENAI_API_KEY not set in the environment."
    
    openai.api_key = api_key

    # if not prompt or not text:
    #     return "Error: no data given"
    
    # Note: top_k is not supported by the OpenAI Chat API.
    response = openai.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ],
        temperature=temperature,
        top_p=top_p
    )
    
    return response.choices[0].message.content

# Example usage:
if __name__ == "__main__":
    system_prompt = "You are a helpful assistant."
    user_input = "Can you explain the benefits of a balanced diet?"
    result = ask_chatgpt_inline(system_prompt, user_input, temperature=0.2, top_p=0.9, top_k=50)
    print("ChatGPT Response:", result)
