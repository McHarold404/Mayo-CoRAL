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

#Load sentence embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# from sentence_transformers import SentenceTransformer, models
# # Load the transformer model
# word_embedding_model = models.Transformer("microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract")
# # Create a pooling layer. This will convert token embeddings to a fixed-size sentence embedding.
# pooling_model = models.Pooling(word_embedding_model.get_word_embedding_dimension())
# # Construct the SentenceTransformer model
# embedding_model = SentenceTransformer(modules=[word_embedding_model, pooling_model])

def retrieve_chunks(query, chunks, top_n=3):
    """ Retrieves top N relevant chunks using BM42 (BM25+ variant). """
    tokenized_chunks = [chunk["content"].lower().split() for chunk in chunks] # else chunk["content"].lower().split()
    bm42 = BM25Plus(tokenized_chunks)
    query_tokens = query.lower().split()
    scores = bm42.get_scores(query_tokens)
    
    ranked_chunks = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [chunk[0] for chunk in ranked_chunks[:top_n]]

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

from transformers import AutoTokenizer, AutoModel
import torch

# def retrieve_chunks(query, chunks, top_n=3):
#     """
#     Retrieves the top N relevant chunks using a ColBERT-style retrieval.
#     The function computes token-level embeddings and applies a late-interaction:
#     for each query token, it takes the maximum similarity over document tokens and sums them.
#     """
#     # Load the ColBERT tokenizer and model (adjust model name as needed)
#     # tokenizer = AutoTokenizer.from_pretrained("castorini/colbert-v2")
#     # model = AutoModel.from_pretrained("castorini/colbert-v2")
    
#     def get_relevance(query_text, document_text):
#         # Tokenize both the query and the document
#         query_inputs = tokenizer(query_text, return_tensors="pt", truncation=True)
#         doc_inputs = tokenizer(document_text, return_tensors="pt", truncation=True)
        
#         with torch.no_grad():
#             # Get token-level embeddings
#             query_embeddings = model(**query_inputs).last_hidden_state  # [1, seq_len_q, hidden_size]
#             doc_embeddings = model(**doc_inputs).last_hidden_state      # [1, seq_len_d, hidden_size]
        
#         # Normalize embeddings
#         query_embeddings = torch.nn.functional.normalize(query_embeddings, p=2, dim=-1)
#         doc_embeddings = torch.nn.functional.normalize(doc_embeddings, p=2, dim=-1)
        
#         # Compute cosine similarities between all query and document token pairs
#         # Resulting shape: [1, seq_len_q, seq_len_d]
#         sims = torch.matmul(query_embeddings, doc_embeddings.transpose(1, 2)).squeeze(0)
        
#         # For each query token, take the maximum similarity over document tokens and sum the results
#         max_sims, _ = sims.max(dim=1)
#         relevance = max_sims.sum().item()
#         return relevance

#     scores = []
#     for chunk in chunks:
#         score = get_relevance(query, chunk["content"])
#         scores.append(score)

#     # Rank the chunks by their relevance scores and return the top N chunks
#     ranked_chunks = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
#     return [chunk for chunk, score in ranked_chunks[:top_n]]


# def retrieve_chunks_monot5(query, chunks, top_n=3):
#     """
#     Retrieves the top N relevant chunks using a monoT5 re-ranking model.
#     Each chunk is scored by feeding a 'Query: ... Document: ...' prompt into monoT5.
#     """
#     # Load the monoT5 tokenizer and model (adjust model name as needed)
#     tokenizer = AutoTokenizer.from_pretrained("castorini/monot5-base-msmarco")
#     model = AutoModelForSeq2SeqLM.from_pretrained("castorini/monot5-base-msmarco")

#     scores = []
#     for chunk in chunks:
#         # Prepare input in the expected format
#         input_text = f"Query: {query} Document: {chunk['content']}"
#         inputs = tokenizer(input_text, return_tensors="pt", truncation=True)
#         # Generate model output (set max_length appropriately)
#         outputs = model.generate(**inputs, max_length=10)
#         # Decode the output. The model is expected to output a numeric score as text.
#         score_str = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
#         try:
#             score = float(score_str)
#         except ValueError:
#             # If conversion fails, assign a default score (e.g., 0)
#             score = 0.0
#         scores.append(score)

#     # Rank the chunks by score (higher is better) and return the top N
#     ranked_chunks = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
#     return [chunk for chunk, score in ranked_chunks[:top_n]]

# # def cluster_chunks(chunks, n_clusters=5):
# #     """
# #     Clusters similar chunks together based on semantic similarity.
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