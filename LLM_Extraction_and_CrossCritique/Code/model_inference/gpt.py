import os
from openai import OpenAI
import json
from token_tracker import add_tokens
import base64
from PIL import Image
from io import BytesIO
from PIL import * # PIL is used for image processing

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
            with open(self.prompt_path, 'r', encoding="utf-8") as file:
                return file.read().strip()
        except FileNotFoundError:
            print(f"Prompt file not found at {self.prompt_path}")
            return ""
        except Exception as e:
            print(f"Error reading prompt file: {str(e)}")
            return ""

    def load_data(self):
        try:
            with open(self.data_path, 'r', encoding="utf-8") as file:
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
            with open(self.meta_data,"r", encoding="utf-8") as json_file:
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
            with open(self.output_path,"w", encoding="utf-8") as json_file:
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

# def ask_chatgpt(text: str, 
#                 prompt_path=None, 
#                 temperature=0.1, 
#                 model_name="gpt-4o", 
#                 key=1, 
#                 history: str = None):
#     from openai import OpenAI
#     import os
#     from dotenv import load_dotenv
    
#     load_dotenv()
#     if key == 1:
#         api_key = os.getenv("OPENAI_API_KEY")
#     elif key == 2:
#         api_key = os.getenv("OPENAI_API_KEY_2")
#     else:
#         return "Error: API key not found"

#     client = OpenAI(api_key=api_key)

#     # Load the system prompt if provided
#     if prompt_path and text:
#         with open(prompt_path, 'r', encoding="utf-8") as file:
#             system_prompt = file.read().strip()
#     else:
#         return "Error: no data given"

#     # Construct base message list
#     messages = [{'role': 'system', 'content': system_prompt}]

#     # Add user-provided history (optional)
#     if history:
#         messages.append({'role': 'user', 'content': history})

#     # Add current input as the next user message
#     messages.append({'role': 'user', 'content': text})

#     # Query OpenAI API
#     response = client.chat.completions.create(
#         model=model_name,
#         messages=messages,
#         temperature=temperature
#     )

#     usage = getattr(response, "usage", None)
#     if usage is not None:
#         add_tokens(usage.prompt_tokens, usage.completion_tokens)

#     return response.choices[0].message.content

def ask_chatgpt(
    text: str,
    prompt_path=None,
    temperature=0.1,
    model_name="gpt-4o",
    key=1,
    history: str = None,
    image = None):
    
    from openai import OpenAI
    import os
    from dotenv import load_dotenv
    from io import BytesIO
    import base64

    load_dotenv()
    # choose API key
    if key == 1:
        api_key = os.getenv("OPENAI_API_KEY")
    elif key == 2:
        api_key = os.getenv("OPENAI_API_KEY_2")
    else:
        return "Error: API key not found"

    client = OpenAI(api_key=api_key)

    # Load system prompt
    if prompt_path and text:
        with open(prompt_path, 'r', encoding="utf-8") as file:
            system_prompt = file.read().strip()
    else:
        return "Error: no data given"

    # Build messages
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.append({"role": "user", "content": history})

    # If an image is provided, convert to base64 and attach
    if image:
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        img_bytes = buffer.read()
        # Some clients accept raw bytes, others want base64-encoded:
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        messages.append({
            "role": "user",
            "content": text,
            "image": img_bytes,       # raw bytes
            # "image_base64": img_b64  # or, if your client expects base64
        })
    else:
        messages.append({"role": "user", "content": text})

    # Call the multimodal-capable model
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature
    )

    # track token usage if available
    usage = getattr(response, "usage", None)
    if usage:
        add_tokens(usage.prompt_tokens, usage.completion_tokens)

    return response.choices[0].message.content
