# from rank_bm25 import BM25Okapi

# def retrieve_chunks(query, chunks, top_n=5):
#     """ Retrieves top N relevant chunks using BM25. """
#     tokenized_chunks = [chunk["content"].lower().split() for chunk in chunks]
#     bm25 = BM25Okapi(tokenized_chunks)
#     query_tokens = query.lower().split()
#     scores = bm25.get_scores(query_tokens)
    
#     ranked_chunks = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
#     return [chunk[0] for chunk in ranked_chunks[:top_n]]

# from sentence_transformers import SentenceTransformer
# from sklearn.cluster import AgglomerativeClustering
# import numpy as np

# # Load sentence embedding model
# embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# def cluster_chunks(chunks, n_clusters=5):
#     """
#     Clusters similar chunks together based on semantic similarity.
#     """
#     chunk_texts = [chunk["content"] for chunk in chunks]
#     chunk_embeddings = embedding_model.encode(chunk_texts)  # Convert chunks to embeddings

#     # Apply Agglomerative Clustering (Hierarchical)
#     clustering_model = AgglomerativeClustering(n_clusters=n_clusters)
#     labels = clustering_model.fit_predict(chunk_embeddings)

#     # Group chunks by their cluster labels
#     clustered_chunks = {}
#     for idx, label in enumerate(labels):
#         if label not in clustered_chunks:
#             clustered_chunks[label] = []
#         clustered_chunks[label].append(chunks[idx])

#     return clustered_chunks

# def sample_chunks_from_clusters(clustered_chunks):
#     """
#     Selects one representative chunk per cluster.
#     """
#     sampled_chunks = []
#     for cluster in clustered_chunks.values():
#         sampled_chunks.append(cluster[0])  # Select the first chunk as the representative

#     return sampled_chunks

###########################################################################################################

from rank_bm25 import BM25Plus
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
import numpy as np

# Load sentence embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def retrieve_chunks(query, chunks, top_n=5):
    """ Retrieves top N relevant chunks using BM42 (BM25+ variant). """
    tokenized_chunks = [chunk["content"].lower().split() for chunk in chunks]
    bm42 = BM25Plus(tokenized_chunks)
    query_tokens = query.lower().split()
    scores = bm42.get_scores(query_tokens)
    
    ranked_chunks = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [chunk[0] for chunk in ranked_chunks[:top_n]]

def cluster_chunks(chunks, n_clusters=5):
    """
    Clusters similar chunks together based on semantic similarity.
    """
    chunk_texts = [chunk["content"] for chunk in chunks]
    chunk_embeddings = embedding_model.encode(chunk_texts)  # Convert chunks to embeddings

    # Apply Agglomerative Clustering (Hierarchical)
    clustering_model = AgglomerativeClustering(n_clusters=n_clusters)
    labels = clustering_model.fit_predict(chunk_embeddings)

    # Group chunks by their cluster labels
    clustered_chunks = {}
    for idx, label in enumerate(labels):
        if label not in clustered_chunks:
            clustered_chunks[label] = []
        clustered_chunks[label].append(chunks[idx])

    return clustered_chunks

def sample_chunks_from_clusters(clustered_chunks):
    """
    Selects one representative chunk per cluster.
    """
    sampled_chunks = []
    for cluster in clustered_chunks.values():
        sampled_chunks.append(cluster[0])  # Select the first chunk as the representative

    return sampled_chunks

# from haystack.nodes import BM25Retriever
# from haystack.document_stores import InMemoryDocumentStore
# from sentence_transformers import SentenceTransformer
# from sklearn.cluster import AgglomerativeClustering
# import numpy as np

# # Load sentence embedding model
# embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# def retrieve_chunks(query, chunks, top_n=5):
#     """ Retrieves top N relevant chunks using BM42 from Haystack. """
#     document_store = InMemoryDocumentStore()
#     document_store.write_documents(chunks)
#     retriever = BM25Retriever(document_store)
#     retrieved_docs = retriever.retrieve(query, top_k=top_n)
#     return retrieved_docs

# def cluster_chunks(chunks, n_clusters=5):
#     """
#     Clusters similar chunks together based on semantic similarity.
#     """
#     chunk_texts = [chunk["content"] for chunk in chunks]
#     chunk_embeddings = embedding_model.encode(chunk_texts)  # Convert chunks to embeddings

#     # Apply Agglomerative Clustering (Hierarchical)
#     clustering_model = AgglomerativeClustering(n_clusters=n_clusters)
#     labels = clustering_model.fit_predict(chunk_embeddings)

#     # Group chunks by their cluster labels
#     clustered_chunks = {}
#     for idx, label in enumerate(labels):
#         if label not in clustered_chunks:
#             clustered_chunks[label] = []
#         clustered_chunks[label].append(chunks[idx])

#     return clustered_chunks

# def sample_chunks_from_clusters(clustered_chunks):
#     """
#     Selects one representative chunk per cluster.
#     """
#     sampled_chunks = []
#     for cluster in clustered_chunks.values():
#         sampled_chunks.append(cluster[0])  # Select the first chunk as the representative

#     return sampled_chunks