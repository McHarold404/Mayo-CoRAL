import os
from openai import OpenAI
import json
from token_tracker import add_tokens
import base64
from PIL import Image
from io import BytesIO
from PIL import * # PIL is used for image processing
import os
import time
import openai
from typing import Optional

client = OpenAI(api_key="")
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")


from typing import Optional
import os, time
from openai import OpenAI

def ask_chatgpt_with_pdf(pdf_path: str,
                         prompt: str,
                         *,
                         api_key: Optional[str] = None,
                         poll: float = 2) -> str:
    """
    Query the contents of *pdf_path* with *prompt* using GPT-4o + file-search tool.

    Returns the assistant’s answer as plain text.
    """
    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    # Upload PDF and create a file object
    with open(pdf_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="assistants")

    # Create assistant with file_search tool (no vector store needed here)
    assistant = client.beta.assistants.create(
        name="PDF-QA",
        model="gpt-4o",
        tools=[{"type": "file_search"}]
    )

    # Create thread with attached file
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
                "attachments": [
                    {"file_id": file_obj.id, "tools": [{"type": "file_search"}]}
                ]
            }
        ]
    )

    # Run assistant and poll until done
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
    
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        print("Run status:", run.status)  # 👈
        if run.status == "completed":
            break
        if run.status in {"failed", "cancelled", "expired"}:
            raise RuntimeError(f"Run failed with status: {run.status}")
        time.sleep(poll)

    # Check messages
    msgs = client.beta.threads.messages.list(thread_id=thread.id)
    print("Messages:", msgs.data)  # 👈

    assistant_msg = next((m for m in msgs.data if m.role == "assistant"), None)
    if not assistant_msg:
        raise RuntimeError("No assistant reply found")

    print("Assistant reply:", assistant_msg.content)  # 👈

    return assistant_msg.content[0].text.value.strip()


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
