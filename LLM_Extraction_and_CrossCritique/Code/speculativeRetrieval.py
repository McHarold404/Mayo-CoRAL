import json
import openai
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
import numpy as np
from rank_bm25 import BM25Okapi
from model_inference.gpt import *  # Explicit import
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


def speculative_rag_pipeline(retreival_query, chunks,columns_info):
    """ Full Speculative RAG: retrieval → clustering → sampling → verification → final answer selection. """
    if not chunks:
        return "No relevant chunks found."


    relevant_chunks = retrieve_chunks(retreival_query, chunks, top_n=min(10, len(chunks)))
    clustered_chunks = relevant_chunks
    #clustered_chunks = cluster_chunks(relevant_chunks, n_clusters=min(5, len(relevant_chunks)))

    # Sample representative chunks
    sampled_chunks = clustered_chunks
    #sampled_chunks = sample_chunks_from_clusters(clustered_chunks)
    print("Sampled chunks:", len(sampled_chunks))  # Debugging line
    if not sampled_chunks:
        return "No sufficient context to generate an answer."

    # Generate responses for each sampled chunk
    responses = []
    print(f"Column values to be extracted: {columns_info}")  # Debugging line
    for chunk in sampled_chunks:  # Limit to 5 chunks
        #print(f"Processing chunk: {chunk['content']}")  # Debugging line
        input_text = f"Column Values to be Extracted: {columns_info} \n\nContext: {chunk['content']}"
        response = ask_gemini(prompt_path = "prompts/draft_answer.txt", text=input_text)
        time.sleep(4)
        if response:
            responses.append(response)

    if not responses:
        return "Failed to generate responses."

    # Select the most relevant response (could use ranking if needed)
    best_answer = select_best_answer(responses=responses,columns_info=columns_info)  # Can be improved using scoring
    #print(f"Best answer selected: {best_answer}")  # Debugging line
    return sampled_chunks,best_answer

def select_best_answer(responses, columns_info):
    """ Selects the best answer from the generated responses. """
    # Combine the candidate responses with newline separation.
    candidates_text = "\n\n".join([f"Response{i}:{response}\n" for i, response in enumerate(responses)])
    prompt_path = "prompts/select_best_answer.txt"
    
    best_answer = ask_gemini(prompt_path=prompt_path, text= candidates_text)
    return best_answer.strip()

