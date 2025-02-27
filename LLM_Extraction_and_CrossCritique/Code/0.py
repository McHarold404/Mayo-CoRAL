from rank_bm25 import BM25Okapi
import json

def retrieve_chunks(query, chunks, top_n=5):
    """ Retrieves top N relevant chunks using BM25. """
    tokenized_chunks = [chunk["content"].lower().split() for chunk in chunks]
    bm25 = BM25Okapi(tokenized_chunks)
    query_tokens = query.lower().split()
    scores = bm25.get_scores(query_tokens)
    
    ranked_chunks = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [chunk[0] for chunk in ranked_chunks[:top_n]]

def main():
    query = "What is the efficacy of Darolutamide in high-risk prostate cancer patients?"
    
    with open("chunks.json", "r", encoding="utf-8") as f:
        chunks = json.load(f)

    relevant_chunks = retrieve_chunks(query, chunks, top_n=5)

    print("\nRelevant Chunks Retrieved:")
    for chunk in relevant_chunks:
        print(f"Page {chunk['page']}: {chunk['content'][:200]}...")

if __name__ == "__main__":
    main()
