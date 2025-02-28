import json
import openai
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
import numpy as np
from rank_bm25 import BM25Okapi
from model_inference.gpt import ask_chatgpt  # Explicit import
from model_inference.gemini import *
from model_inference.llama import * 
import sys
import os
from dotenv import load_dotenv  # Correct import

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from k_retrieval import retrieve_chunks  # Now Python should find it

# Load environment variables
load_dotenv()

# OpenAI Client Setup (New API Format)
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is missing! Please set it in the .env file.")

client = openai.OpenAI(api_key=api_key)  # New API format

# Sentence Transformer Model for embeddings
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def cluster_chunks(chunks, n_clusters=5):
    """ Groups similar chunks together based on semantic similarity. """
    if not chunks:
        return {}  # Return empty dictionary if no chunks found

    chunk_texts = [chunk["content"] for chunk in chunks]
    chunk_embeddings = embedding_model.encode(chunk_texts)

    clustering_model = AgglomerativeClustering(n_clusters=min(n_clusters, len(chunks)))  # Avoid errors
    labels = clustering_model.fit_predict(chunk_embeddings)

    clustered_chunks = {}
    for idx, label in enumerate(labels):
        clustered_chunks.setdefault(label, []).append(chunks[idx])

    return clustered_chunks

def sample_chunks_from_clusters(clustered_chunks):
    """ Selects one representative chunk per cluster. """
    return [cluster[0] for cluster in clustered_chunks.values() if cluster]


def speculative_rag_pipeline(query, chunks,columns_info):
    """ Full Speculative RAG: retrieval → clustering → sampling → verification → final answer selection. """
    if not chunks:
        return "No relevant chunks found."

    # Retrieve relevant chunks
    print(columns_info)
    relevant_chunks = retrieve_chunks(query, chunks, top_n=min(10, len(chunks)))

    # Cluster retrieved chunks
    clustered_chunks = cluster_chunks(relevant_chunks, n_clusters=min(5, len(relevant_chunks)))

    # Sample representative chunks
    sampled_chunks = sample_chunks_from_clusters(clustered_chunks)

    if not sampled_chunks:
        return "No sufficient context to generate an answer."

    # Generate responses for each sampled chunk
    responses = []
    for chunk in sampled_chunks[:5]:  # Limit to 5 chunks
        print(f"Query: {query}")  # Debugging line
        print(f"Processing chunk: {chunk['content']}")  # Debugging line
        input_text = f"Query: {query}\n\nContext: {chunk['content']}"
        response = ask_chatgpt(prompt_path = "prompts/draft_answer.txt", text=input_text)
        # print("****************************")
        # print(f"Response for chunk: {response}")  # Debugging line
        # print("****************************")
        if response:
            responses.append(response)

    if not responses:
        return "Failed to generate responses."

    # Select the most relevant response (could use ranking if needed)
    best_answer = select_best_answer(responses=responses,columns_info=columns_info)  # Can be improved using scoring
    print(f"Best answer selected: {best_answer}")  # Debugging line
    return best_answer

def select_best_answer(responses, columns_info):
    """
    Selects the best candidate response for extracting structured information for the specified columns.
    
    Parameters:
      - responses: A list of candidate JSON response strings.
      - columns_info: A list of dictionaries for the group, each with "Column Name" and "Definition".
    
    Returns:
      - A JSON string representing the best candidate response.
    
    This function calls ask_chatgpt using a system prompt from a file and passes the variable parts (column definitions and candidate responses) via the text parameter.
    """
    # Build a text block with the columns and their definitions.
    columns_text = "\n".join(
        [f"{col['Column Name']}: {col['Definition']}" for col in columns_info]
    )
    
    # Combine the candidate responses with newline separation.
    candidates_text = "\n".join(responses)
    
    # Construct the variable text to be passed alongside the system prompt.
    text_param = f"""
Columns and their Definitions:
{columns_text}

Candidate Responses:
{candidates_text}

Instructions:
- Review each candidate JSON response for completeness, accuracy, and clarity.
- Evaluate which candidate best extracts the required values for the above columns.
- Return only the selected JSON object exactly as is, with no additional commentary or explanation.
"""
    # The prompt file (system prompt) should contain the static instructions for best answer selection.
    prompt_path = "prompts/select_best_answer.txt"
    
    best_answer = ask_chatgpt(prompt_path=prompt_path, text=text_param)
    return best_answer.strip()
# def main():
#     query = "What is the efficacy of Darolutamide in high-risk prostate cancer patients?"
#     try:
#         with open("db/Document_Name/hybrid_chunks.json", "r", encoding="utf-8") as f:
#             chunks = json.load(f)
#     except FileNotFoundError:
#         print("Error: hybrid_chunks.json not found.")
#         return
#     except json.JSONDecodeError:
#         print("Error: JSON file is not properly formatted.")
#         return

#     best_response = speculative_rag_pipeline(query, chunks)
#     print("\nFinal Best Answer:\n", best_response)

# if __name__ == "__main__":
#     main()
