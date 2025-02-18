import numpy as np
import json
import openai
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
from rank_bm25 import BM25Okapi
import spacy

# Load NLP models
nlp = spacy.load("en_core_web_sm")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# OpenAI API setup (replace with your API key)
OPENAI_API_KEY = "your-api-key"
openai.api_key = OPENAI_API_KEY

### 1️ CHUNK RETRIEVAL FUNCTION ###
def retrieve_relevant_chunks(query, chunks, top_n=10):
    """
    Retrieves the most relevant chunks using BM25 for keyword matching 
    and embeddings for semantic similarity.
    """
    chunk_texts = [chunk["content"] for chunk in chunks]
    
    # Tokenize for BM25
    tokenized_chunks = [text.lower().split() for text in chunk_texts]
    bm25 = BM25Okapi(tokenized_chunks)
    query_tokens = query.lower().split()
    
    # Get BM25 scores
    bm25_scores = bm25.get_scores(query_tokens)
    
    # Get embeddings for semantic similarity
    chunk_embeddings = embedding_model.encode(chunk_texts)
    query_embedding = embedding_model.encode([query])
    embedding_scores = cosine_similarity(query_embedding, chunk_embeddings)[0]
    
    # Combine scores (weighted sum)
    final_scores = 0.5 * np.array(bm25_scores) + 0.5 * np.array(embedding_scores)
    
    # Select top N chunks
    top_indices = np.argsort(final_scores)[-top_n:]
    top_chunks = [chunks[i] for i in top_indices]
    
    return top_chunks

### 2️ CLUSTERING FUNCTION ###
def cluster_chunks(chunks, n_clusters=5):
    """
    Groups chunks into clusters based on semantic similarity.
    """
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

### 3️ SAMPLE CHUNKS FROM CLUSTERS ###
def sample_chunks_from_clusters(clustered_chunks):
    """
    Samples one representative chunk from each cluster for diversity.
    """
    sampled_chunks = []
    for label, cluster_chunks in clustered_chunks.items():
        sampled_chunks.append(cluster_chunks[0])  # Pick the first chunk in each cluster
    return sampled_chunks

### 4️ SPECULATIVE ANSWER DRAFTING (LIGHT MODEL) ###
def draft_answers(query, chunks, model="gpt-3.5-turbo"):
    """
    Generates speculative answer drafts using a smaller LLM.
    """
    responses = []
    for chunk in chunks:
        prompt = f"Answer this question based on the provided context:\n\nContext:\n{chunk['content']}\n\nQuestion:\n{query}\n\nAnswer:"
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        responses.append(response["choices"][0]["message"]["content"])
    return responses

### 5️ VERIFY ANSWERS USING A GENERALIST MODEL ###
def verify_answers(query, drafts, model="gpt-4"):
    """
    Verifies speculative drafts using a generalist LLM.
    """
    verified_answers = []
    for draft in drafts:
        prompt = f"Evaluate the following answer for accuracy and completeness based on the question:\n\nQuestion: {query}\n\nAnswer: {draft}\n\nDoes this answer correctly address the question? Provide a confidence score (0-1) and reasoning."
        
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        verified_answers.append({
            "draft": draft,
            "evaluation": response["choices"][0]["message"]["content"]
        })
    
    return verified_answers

### 6️ SELECT BEST RESPONSE BASED ON CONFIDENCE SCORE ###
def select_best_answer(verified_answers):
    """
    Selects the best answer based on confidence score.
    """
    best_answer = None
    best_score = 0
    
    for answer in verified_answers:
        # Extract confidence score from evaluation
        score_line = [line for line in answer["evaluation"].split("\n") if "confidence score" in line.lower()]
        if score_line:
            score = float(score_line[0].split(":")[-1].strip())
            if score > best_score:
                best_score = score
                best_answer = answer["draft"]
    
    return best_answer

### 7️ FULL PIPELINE FUNCTION ###
def speculative_rag_pipeline(query, chunks):
    """
    Full Speculative RAG pipeline: retrieval → clustering → sampling → drafting → verification → final answer selection.
    """
    print("\n Retrieving Relevant Chunks...")
    relevant_chunks = retrieve_relevant_chunks(query, chunks, top_n=10)
    
    print("\n Clustering Chunks...")
    clustered_chunks = cluster_chunks(relevant_chunks, n_clusters=5)
    
    print("\n Sampling Chunks from Clusters...")
    sampled_chunks = sample_chunks_from_clusters(clustered_chunks)
    
    print("\n Generating Speculative Answer Drafts...")
    drafts = draft_answers(query, sampled_chunks)
    
    print("\n Verifying Drafts Using Generalist Model...")
    verified_answers = verify_answers(query, drafts)
    
    print("\n Selecting Best Answer...")
    best_answer = select_best_answer(verified_answers)
    
    return best_answer

### 8️ EXAMPLE USAGE ###
# Load chunks from JSON file (assuming you saved chunked data previously)
with open("chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

# Query
query = "What is the efficacy of Darolutamide in high-risk prostate cancer patients?"

# Run Speculative RAG Pipeline
best_response = speculative_rag_pipeline(query, chunks)

# Output Result
print("\n Final Best Answer:\n", best_response)
