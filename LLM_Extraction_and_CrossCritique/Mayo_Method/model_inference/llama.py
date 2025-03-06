import os
from groq import Groq
class LlamaBot:
    def __init__(self, api_key=None, model="llama3-70b-8192", 
                 data_path=None,
                 start_line = None,
                 end_line = None,
                 limit_rows = None,
                 data_string = None,
                 prompt_path=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required. Set it in the constructor or as an environment variable 'GROQ_API_KEY'")
        self.client = Groq(api_key=self.api_key)
        self.model = model
        self.limit_rows = limit_rows
        self.data_string = data_string
        self.start_line = start_line
        self.end_line = end_line
        self.data_path = data_path
        self.prompt_path = prompt_path

    def get_api_response(self, user_message):
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],
                model=self.model
            )
            return chat_completion.choices[0].message.content
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
            if self.data_string is not None:
                print('Data file not found, returning string used')
                return [self.data_string]
            else:
                print(f"Data file not found at {self.data_path}")
                return []
        except Exception as e:
            print(f"Error reading data file: {str(e)}")
            return []

    def run_inference(self):
        print("Starting inference")
        data = self.load_data()
        prompt = self.load_prompt()
        
        if not data:
            print("No data to process. Exiting.")
            return
        
        if not prompt:
            print("No prompt loaded. Exiting.")
            return
        results = []
        
        for i, point in enumerate(data, 1):
            if self.start_line is not None:
                if i < self.start_line:
                    continue
            if self.end_line is not None:
                if i > self.end_line:
                    continue
            if( self.limit_rows is not None and i > self.limit_rows):
                return results
            final_input = f"{prompt}:\n{point}"
            response = self.get_api_response(final_input)
            results.append({'data_point': i,'input': point,'response': response})
            print(f"Data point {i}:")
            #print(f"Input: {point}")
            #print(f"AI Response: {response}")
            #print("-" * 50)
        return results


def ask_llama(text, prompt_path=None, api_key=""):
    # Check if a prompt path is provided and read the prompt text
    if prompt_path and text:
        with open(prompt_path, 'r') as file:
            prompt = file.read().strip()

    else:
        return ("Error: Prompt or text missing")
    # Initialize the Llama API client with the provided API key
    client = Groq(api_key=api_key)  # Ensure Llama client is properly initialized

    # Model configuration - replace 'llama-model-name' with the specific model if needed
    model_name = "llama3-70b-8192"  # Replace with the actual Llama model identifier
    
    try:
        # Send the prompt to the model
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role" : "system",
                    "content" : prompt,
                },
                {
                    "role": "user",
                    "content": text,
                }
                
            ],model=model_name, temperature=0.2,top_p=0.2)
        # Return the response content
        return chat_completion.choices[0].message.content

    except Exception as e:
        return f"An error occurred: {str(e)}"