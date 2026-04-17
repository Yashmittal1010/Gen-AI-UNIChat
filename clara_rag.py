"""
Clara RAG - Lightweight Retrieval-Augmented Generation Engine
Uses TF-IDF vectorization for fast, dependency-light semantic search.
No heavy embedding models or external vector DBs needed.
"""

import json
import os
import pickle
import re
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ClaraRAG:
    """Lightweight RAG engine using TF-IDF vectors stored in a local file (VectorDB Lite)."""

    def __init__(self, knowledge_path: str = "knowledge_base.json", cache_dir: str = ".clara_cache"):
        self.knowledge_path = knowledge_path
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        self.entries = []
        self.corpus = []
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True,
        )
        self.tfidf_matrix = None

        self._load_knowledge_base()
        self._build_or_load_index()

    def _load_knowledge_base(self):
        """Load knowledge base from JSON."""
        with open(self.knowledge_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.entries = data["entries"]

        # Build corpus: combine question + answer + section + category for richer matching
        for entry in self.entries:
            text = f"{entry.get('question', '')} {entry.get('answer', '')} {entry.get('section', '')} {entry.get('category', '')}"
            self.corpus.append(text.lower())

        print(f"[Clara RAG] Loaded {len(self.entries)} knowledge entries")

    def _build_or_load_index(self):
        """Build TF-IDF index or load from cache (VectorDB Lite)."""
        cache_file = self.cache_dir / "tfidf_index.pkl"
        kb_mtime = os.path.getmtime(self.knowledge_path)

        # Check if cache exists and is fresh
        if cache_file.exists():
            cache_mtime = os.path.getmtime(cache_file)
            if cache_mtime > kb_mtime:
                with open(cache_file, "rb") as f:
                    cached = pickle.load(f)
                    self.vectorizer = cached["vectorizer"]
                    self.tfidf_matrix = cached["matrix"]
                    print("[Clara RAG] Loaded index from cache (VectorDB Lite)")
                    return

        # Build fresh index
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)

        # Save to cache (VectorDB Lite - file-based vector store)
        with open(cache_file, "wb") as f:
            pickle.dump({
                "vectorizer": self.vectorizer,
                "matrix": self.tfidf_matrix,
            }, f)
        print(f"[Clara RAG] Built and cached TF-IDF index ({self.tfidf_matrix.shape})")

    def query(self, user_query: str, top_k: int = 3, threshold: float = 0.05) -> list[dict]:
        """
        Retrieve top-k relevant entries for a user query.

        Returns list of dicts with 'entry' and 'score' keys.
        """
        # Normalize query
        clean_query = re.sub(r"[^\w\s]", "", user_query.lower())
        query_vec = self.vectorizer.transform([clean_query])

        # Compute similarities
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Get top-k above threshold
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = []

        for idx in top_indices:
            score = float(similarities[idx])
            if score >= threshold:
                results.append({
                    "entry": self.entries[idx],
                    "score": round(score, 4),
                })

        return results

    def get_context(self, user_query: str, top_k: int = 3) -> str:
        """Get formatted context string for LLM prompt construction."""
        results = self.query(user_query, top_k=top_k)

        if not results:
            return "No specific information found. Suggest contacting MUJ directly: Toll-free 18001020128, Email admissions@jaipur.manipal.edu, Website jaipur.manipal.edu"

        context_parts = []
        for r in results:
            entry = r["entry"]
            context_parts.append(f"[{entry['section']} - {entry['category']}]\nQ: {entry['question']}\nA: {entry['answer']}")

        return "\n\n".join(context_parts)


# Quick test
if __name__ == "__main__":
    rag = ClaraRAG()
    test_queries = [
        "What are the hostel fees?",
        "How are placements?",
        "Tell me about CSE",
        "How do I apply?",
        "Is there ragging?",
    ]
    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {q}")
        results = rag.query(q)
        for r in results:
            print(f"  [{r['score']:.3f}] {r['entry']['section']}/{r['entry']['category']}: {r['entry']['question']}")
