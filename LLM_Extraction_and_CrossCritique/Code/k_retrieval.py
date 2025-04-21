
# from rank_bm25 import BM25Plus
# from sentence_transformers import SentenceTransformer
# from sklearn.cluster import AgglomerativeClustering
# import numpy as np

# embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
# def retrieve_chunks(query, chunks, top_n=3):
#     """ Retrieves top N relevant chunks using BM42 (BM25+ variant). """
#     tokenized_chunks = [chunk["content"].lower().split() for chunk in chunks] # else chunk["content"].lower().split()
#     bm42 = BM25Plus(tokenized_chunks)
#     query_tokens = query.lower().split()
#     scores = bm42.get_scores(query_tokens)
    
#     ranked_chunks = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
#     return [chunk[0] for chunk in ranked_chunks[:top_n]]

# from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# from transformers import AutoTokenizer, AutoModel
# import torch

from rank_bm25 import BM25Plus
from sentence_transformers import SentenceTransformer
from scipy import spatial

# Switch to a biomedical model for better accuracy
embedding_model = SentenceTransformer("microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract")
bm25_instance = None
tokenized_chunks_cache = None
chunk_embeddings = None

def setup_retrieval(chunks):
    """Precompute tokenized chunks, BM25Plus, and embeddings once."""
    global bm25_instance, tokenized_chunks_cache, chunk_embeddings
    tokenized_chunks_cache = [chunk["content"].lower().split() for chunk in chunks]
    bm25_instance = BM25Plus(tokenized_chunks_cache)
    chunk_embeddings = embedding_model.encode(
        [chunk["content"] for chunk in chunks], 
        convert_to_numpy=True,
        show_progress_bar=False
    )

def retrieve_chunks(query, chunks, top_n=3):
    """Retrieve top N relevant chunks using hybrid BM25Plus + embeddings."""
    global bm25_instance, tokenized_chunks_cache, chunk_embeddings
    if bm25_instance is None or tokenized_chunks_cache is None or chunk_embeddings is None:
        setup_retrieval(chunks)  # Fallback if not precomputed
    
    # BM25 scoring
    query_tokens = query.lower().split()
    bm25_scores = bm25_instance.get_scores(query_tokens)
    
    # Embedding scoring
    query_embedding = embedding_model.encode([query], convert_to_numpy=True)[0]
    embedding_scores = [
        1 - spatial.distance.cosine(query_embedding, emb) 
        for emb in chunk_embeddings
    ]
    
    # Combine scores (adjust weights as needed)
    combined_scores = [
        0.7 * bm25 + 0.3 * emb 
        for bm25, emb in zip(bm25_scores, embedding_scores)
    ]
    
    # Optional metadata filter (uncomment if chunks have metadata)
    # if "metadata" in chunks[0]:
    #     query_keywords = set(query.lower().split())
    #     filtered_indices = [
    #         i for i, chunk in enumerate(chunks)
    #         if any(kw in chunk["metadata"].get("section", "").lower() for kw in query_keywords)
    #     ]
    #     if filtered_indices:
    #         combined_scores = [combined_scores[i] if i in filtered_indices else -float("inf") for i in range(len(chunks))]
    
    ranked_chunks = sorted(zip(chunks, combined_scores), key=lambda x: x[1], reverse=True)
    return [chunk[0] for chunk in ranked_chunks[:top_n]]

def reset_retrieval():
    """Reset for a new document."""
    global bm25_instance, tokenized_chunks_cache, chunk_embeddings
    bm25_instance = None
    tokenized_chunks_cache = None
    chunk_embeddings = None