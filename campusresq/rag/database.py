"""
Hybrid RAG Engine with BM25 Lexical Matching, Dense Vector Scoring, and RRF Reranking.
Conforms strictly to IEEE 1016-2009 SDD §4.2, §4.3 and SRS §3.3, §5.2.
"""

from typing import List, Dict, Any, Optional
import math
import re
from rank_bm25 import BM25Okapi
from .knowledge_base import CAMPUS_KNOWLEDGE_DOCS

def tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())

def build_dense_embedding(text: str, vocab: List[str]) -> List[float]:
    """
    Lightweight deterministic dense vector representation for fast low-latency matching.
    """
    tokens = tokenize(text)
    token_set = set(tokens)
    vec = []
    for word in vocab:
        if word in token_set:
            # Term frequency / length normalized
            count = tokens.count(word)
            vec.append(count / (1.0 + len(tokens)))
        else:
            vec.append(0.0)
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    return max(0.0, min(1.0, dot))

class HybridRAGDatabase:
    """
    In-memory vector database with BM25 lexical index and dense similarity search.
    Implements Reciprocal Rank Fusion (RRF) and cross-similarity reranking.
    """
    def __init__(self, documents: Optional[List[Dict[str, Any]]] = None):
        self.documents = documents or CAMPUS_KNOWLEDGE_DOCS
        self._build_indexes()
        
    def _build_indexes(self):
        # Extract corpus for BM25
        self.corpus = []
        all_words = set()
        for doc in self.documents:
            full_text = f"{doc['title']} {doc['content_text']} {' '.join(doc.get('keywords', []))}"
            toks = tokenize(full_text)
            self.corpus.append(toks)
            all_words.update(toks)
            
        self.vocab = sorted(list(all_words))
        self.bm25 = BM25Okapi(self.corpus)
        
        # Build dense representations
        self.dense_vectors = []
        for doc in self.documents:
            full_text = f"{doc['title']} {doc['content_text']} {' '.join(doc.get('keywords', []))}"
            vec = build_dense_embedding(full_text, self.vocab)
            self.dense_vectors.append(vec)

    def hybrid_search(
        self, 
        query: str, 
        building_id: Optional[str] = None, 
        hazard_type: Optional[str] = None, 
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval using BM25 and dense similarity with Reciprocal Rank Fusion (RRF).
        RRF(d) = 1 / (60 + r_dense(d)) + 1 / (60 + r_bm25(d))
        """
        q_tokens = tokenize(query)
        if not q_tokens:
            q_tokens = ["emergency"]
            
        # 1. BM25 Scores
        bm25_scores = self.bm25.get_scores(q_tokens)
        bm25_ranked = sorted(
            range(len(self.documents)), 
            key=lambda i: bm25_scores[i], 
            reverse=True
        )
        bm25_rank_map = {idx: rank + 1 for rank, idx in enumerate(bm25_ranked)}
        
        # 2. Dense Vector Scores
        q_dense = build_dense_embedding(query, self.vocab)
        dense_scores = [cosine_similarity(q_dense, d_vec) for d_vec in self.dense_vectors]
        dense_ranked = sorted(
            range(len(self.documents)), 
            key=lambda i: dense_scores[i], 
            reverse=True
        )
        dense_rank_map = {idx: rank + 1 for rank, idx in enumerate(dense_ranked)}
        
        # 3. Reciprocal Rank Fusion (RRF) with Building & Hazard Boosting
        candidates = []
        for idx, doc in enumerate(self.documents):
            # Check metadata filters
            applicable_bldgs = doc.get("applicable_buildings", ["ALL"])
            bldg_match = (building_id is None) or ("ALL" in applicable_bldgs) or (building_id in applicable_bldgs)
            
            applicable_hazards = doc.get("hazard_categories", ["ALL"])
            hazard_match = (hazard_type is None) or ("ALL" in applicable_hazards) or (hazard_type.upper() in [h.upper() for h in applicable_hazards])
            
            filter_boost = 1.0
            if bldg_match:
                filter_boost += 0.25
            if hazard_match:
                filter_boost += 0.25
                
            r_dense = dense_rank_map[idx]
            r_bm25 = bm25_rank_map[idx]
            
            rrf_score = ((1.0 / (60.0 + r_dense)) + (1.0 / (60.0 + r_bm25))) * filter_boost
            
            # Cross-encoder simulated score
            relevance_score = min(1.0, (dense_scores[idx] * 0.5) + (min(1.0, bm25_scores[idx] / 10.0) * 0.5) + (0.1 if bldg_match else 0.0))
            
            candidates.append({
                "doc_id": doc["id"],
                "rrf_score": float(round(float(rrf_score), 6)),
                "relevance_score": float(round(float(relevance_score), 4)),
                "title": doc["title"],
                "document_type": doc["document_type"],
                "section_id": doc["section_id"],
                "page_number": doc["page_number"],
                "content_text": doc["content_text"],
                "applicable_buildings": doc.get("applicable_buildings", []),
                "hazard_categories": doc.get("hazard_categories", [])
            })
            
        candidates.sort(key=lambda x: (x["relevance_score"], x["rrf_score"]), reverse=True)
        return candidates[:top_k]

# Global singleton
rag_db = HybridRAGDatabase()
