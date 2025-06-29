
# from rank_bm25 import BM25Plus
# from sentence_transformers import SentenceTransformer
# from sklearn.cluster import AgglomerativeClustering
# import numpy as np
# embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
# from rank_bm25 import BM25Plus
# from sentence_transformers import SentenceTransformer
# from scipy import spatial

# # Switch to a biomedical model for better accuracy
# embedding_model = SentenceTransformer("microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract")
# bm25_instance = None
# tokenized_chunks_cache = None
# chunk_embeddings = None

# def setup_retrieval(chunks):
#     """Precompute tokenized chunks, BM25Plus, and embeddings once."""
#     global bm25_instance, tokenized_chunks_cache, chunk_embeddings
#     tokenized_chunks_cache = [chunk["content"].lower().split() for chunk in chunks]
#     bm25_instance = BM25Plus(tokenized_chunks_cache)
#     chunk_embeddings = embedding_model.encode(
#         [chunk["content"] for chunk in chunks], 
#         convert_to_numpy=True,
#         show_progress_bar=False
#     )

# def retrieve_chunks(query, chunks, top_n=3):
#     """Retrieve top N relevant chunks using hybrid BM25Plus + embeddings."""
#     global bm25_instance, tokenized_chunks_cache, chunk_embeddings
#     if bm25_instance is None or tokenized_chunks_cache is None or chunk_embeddings is None:
#         setup_retrieval(chunks)  # Fallback if not precomputed
    
#     # BM25 scoring
#     query_tokens = query.lower().split()
#     bm25_scores = bm25_instance.get_scores(query_tokens)
    
#     # Embedding scoring
#     query_embedding = embedding_model.encode([query], convert_to_numpy=True)[0]
#     embedding_scores = [
#         1 - spatial.distance.cosine(query_embedding, emb) 
#         for emb in chunk_embeddings
#     ]
    
#     # Combine scores (adjust weights as needed)
#     combined_scores = [
#         0.7 * bm25 + 0.3 * emb 
#         for bm25, emb in zip(bm25_scores, embedding_scores)
#     ]
    
#     # Optional metadata filter (uncomment if chunks have metadata)
#     # if "metadata" in chunks[0]:
#     #     query_keywords = set(query.lower().split())
#     #     filtered_indices = [
#     #         i for i, chunk in enumerate(chunks)
#     #         if any(kw in chunk["metadata"].get("section", "").lower() for kw in query_keywords)
#     #     ]
#     #     if filtered_indices:
#     #         combined_scores = [combined_scores[i] if i in filtered_indices else -float("inf") for i in range(len(chunks))]
#     ranked_chunks = sorted(zip(chunks, combined_scores), key=lambda x: x[1], reverse=True)
#     return [chunk[0] for chunk in ranked_chunks[:top_n]]


# def reset_retrieval():
#     """Reset for a new document."""
#     global bm25_instance, tokenized_chunks_cache, chunk_embeddings
#     bm25_instance = None
#     tokenized_chunks_cache = None
#     chunk_embeddings = None

# hybrid_retrieval.py  –  openai-python ≥1.84.0
from __future__ import annotations
import os, re
from typing import List, Dict
import numpy as np
from rank_bm25 import BM25Plus
from scipy import spatial
from dotenv import load_dotenv
from openai import OpenAI

# ── env / constants ───────────────────────────────────────────────────────────
load_dotenv()
client = OpenAI()                          # uses OPENAI_API_KEY from .env
MODEL      = "text-embedding-ada-002"
EMB_DIM    = 1536
MAX_CHARS  = 32_000                        # crude ≈ 8 k-token clip
BATCH_SIZE = 256                           # well below 2048-item limit

# ── caches ────────────────────────────────────────────────────────────────────
_bm25: BM25Plus | None = None
_tokenized: List[List[str]] | None = None
_embeds: np.ndarray | None = None

# ── util ──────────────────────────────────────────────────────────────────────
def _clean(txt: str) -> str:
    """Strip, delete control chars, truncate hard-limit."""
    if txt is None:
        return ""
    txt = re.sub(r"[\x00-\x1F\x7F]", " ", txt).strip()
    return txt[:MAX_CHARS]

def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]

# ── embedding with placeholders ───────────────────────────────────────────────
def _embed(texts: List[str]) -> np.ndarray:
    """Return an N×1536 matrix; rows with empty input stay all-zero."""
    cleaned = [_clean(t) for t in texts]
    keep_idx = [i for i, t in enumerate(cleaned) if t]   # indices to embed
    mat = np.zeros((len(texts), EMB_DIM), dtype=np.float32)

    if keep_idx:                                         # only if something to embed
        keep_txt = [cleaned[i] for i in keep_idx]
        vecs: List[List[float]] = []

        for batch in _chunks(keep_txt, BATCH_SIZE):
            resp = client.embeddings.create(model=MODEL, input=batch)
            vecs.extend([d.embedding for d in sorted(resp.data, key=lambda d: d.index)])

        mat[keep_idx] = np.asarray(vecs, dtype=np.float32)
    return mat

# ── public API ────────────────────────────────────────────────────────────────
def setup_retrieval(chunks: List[Dict[str, str]]) -> None:
    global _bm25, _tokenized, _embeds
    _tokenized = [c["content"].lower().split() for c in chunks]
    _bm25 = BM25Plus(_tokenized)
    _embeds = _embed([c["content"] for c in chunks])

def retrieve_chunks(query: str,
                    chunks: List[Dict[str, str]],
                    top_n: int = 5) -> List[Dict[str, str]]:
    global _bm25, _embeds
    if _bm25 is None or _embeds is None:
        setup_retrieval(chunks)

    bm25_scores = _bm25.get_scores(query.lower().split())

    q_vec = _embed([query])[0]              # single-vector (1536,)
    # cosine distance with zero row yields nan; replace with 0 similarity
    cos = 1 - spatial.distance.cdist([q_vec], _embeds, metric="cosine")[0]
    cos = np.nan_to_num(cos, nan=0.0)

    hybrid = 0.7 * bm25_scores + 0.3 * cos
    ranked = sorted(zip(chunks, hybrid), key=lambda x: x[1], reverse=True)
    return [c for c, _ in ranked[:top_n]]

def reset_retrieval() -> None:
    global _bm25, _tokenized, _embeds
    _bm25 = _tokenized = _embeds = None
