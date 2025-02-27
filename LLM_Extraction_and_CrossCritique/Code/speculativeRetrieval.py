import json
import openai
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
import numpy as np
from rank_bm25 import BM25Okapi

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from k_retrieval import retrieve_chunks  # Now Python should find it




openai.api_key = "your-api-key" # or like try gemini

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def cluster_chunks(chunks, n_clusters=5):
    """ Groups similar chunks together based on semantic similarity. """
    chunk_texts = [chunk["content"] for chunk in chunks]
    chunk_embeddings = embedding_model.encode(chunk_texts)

    clustering_model = AgglomerativeClustering(n_clusters=n_clusters)
    labels = clustering_model.fit_predict(chunk_embeddings)

    clustered_chunks = {}
    for idx, label in enumerate(labels):
        if label not in clustered_chunks:
            clustered_chunks[label] = []
        clustered_chunks[label].append(chunks[idx])

    return clustered_chunks

def sample_chunks_from_clusters(clustered_chunks):
    """ Selects one representative chunk per cluster. """
    return [cluster[0] for cluster in clustered_chunks.values()]

def speculative_rag_pipeline(query, chunks):
    """ Full Speculative RAG: retrieval → clustering → sampling → verification → final answer selection. """
    relevant_chunks = retrieve_chunks(query, chunks, top_n=10)
    clustered_chunks = cluster_chunks(relevant_chunks, n_clusters=5)
    sampled_chunks = sample_chunks_from_clusters(clustered_chunks)

    best_answer = None
    for chunk in sampled_chunks:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Answer this based on context: {chunk['content']}"}],
            max_tokens=200
        )
        best_answer = response["choices"][0]["message"]["content"]
    
    return best_answer

def main():
    query = "What is the efficacy of Darolutamide in high-risk prostate cancer patients?"
    
    with open("hybrid_chunks.json", "r", encoding="utf-8") as f:
        chunks = json.load(f)

    best_response = speculative_rag_pipeline(query, chunks)
    print("\nFinal Best Answer:\n", best_response)

if __name__ == "__main__":
    main()
