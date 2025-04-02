
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

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")  # Kept for future use
bm25_instance = None
tokenized_chunks_cache = None

def setup_retrieval(chunks):
    """Precompute tokenized chunks and initialize BM25Plus once."""
    global bm25_instance, tokenized_chunks_cache
    tokenized_chunks_cache = [chunk["content"].lower().split() for chunk in chunks]
    bm25_instance = BM25Plus(tokenized_chunks_cache)

def retrieve_chunks(query, chunks, top_n=3):
    """Retrieve top N relevant chunks using precomputed BM25Plus."""
    global bm25_instance, tokenized_chunks_cache
    if bm25_instance is None or tokenized_chunks_cache is None:
        setup_retrieval(chunks)  # Fallback if not precomputed
    
    query_tokens = query.lower().split()
    scores = bm25_instance.get_scores(query_tokens)
    
    ranked_chunks = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [chunk[0] for chunk in ranked_chunks[:top_n]]

def reset_retrieval():
    """Reset for a new document."""
    global bm25_instance, tokenized_chunks_cache
    bm25_instance = None
    tokenized_chunks_cache = None