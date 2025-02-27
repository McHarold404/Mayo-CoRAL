import json
import openai
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
import numpy as np
from rank_bm25 import BM25Okapi
from model_inference.gpt import ask_chatgpt_inline  # Explicit import
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


def speculative_rag_pipeline(query, chunks):
    """ Full Speculative RAG: retrieval → clustering → sampling → verification → final answer selection. """
    if not chunks:
        return "No relevant chunks found."

    # Retrieve relevant chunks
    relevant_chunks = retrieve_chunks(query, chunks, top_n=min(10, len(chunks)))

    # Cluster retrieved chunks
    clustered_chunks = cluster_chunks(relevant_chunks, n_clusters=min(5, len(relevant_chunks)))

    # Sample representative chunks
    sampled_chunks = sample_chunks_from_clusters(clustered_chunks)

    if not sampled_chunks:
        return "No sufficient context to generate an answer."

    # Generate responses for each sampled chunk
    responses = []
    for chunk in sampled_chunks:
        response = ask_chatgpt_inline(prompt="Answer this based on context", text=chunk["content"])
        if response:
            responses.append(response)

    if not responses:
        return "Failed to generate responses."

    # Select the most relevant response (could use ranking if needed)
    best_answer = select_best_answer(responses=responses)  # Can be improved using scoring

    return best_answer

def select_best_answer(responses):
    """ Selects the best answer from the generated responses. """
    # Placeholder for a more sophisticated ranking mechanism
    input_text = "\n".join(responses)
    best_answer = ask_chatgpt_inline(prompt="Select the best answer", text=responses) ## To be improved, use  proper prompt for this task
    return best_answer 

def main():
    query = "What is the efficacy of Darolutamide in high-risk prostate cancer patients?"
    try:
        with open("db/Document_Name/hybrid_chunks.json", "r", encoding="utf-8") as f:
            chunks = json.load(f)
    except FileNotFoundError:
        print("Error: hybrid_chunks.json not found.")
        return
    except json.JSONDecodeError:
        print("Error: JSON file is not properly formatted.")
        return

    best_response = speculative_rag_pipeline(query, chunks)
    print("\nFinal Best Answer:\n", best_response)

if __name__ == "__main__":
    main()
