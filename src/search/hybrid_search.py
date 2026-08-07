"""
Feature 11 (query side) + Feature 14: Unified Search
Implements every query type requested:
  - Match Query        -> match_search()
  - Multi-Match Query   -> bm25_search() (see bm25_search.py)
  - Boosting Query      -> boosting_search()
  - Filter Query        -> filtered_search()
  - Sorting Query       -> sorted_search()
  - Vector (kNN) Query  -> vector_search()
  - Hybrid (BM25+kNN)   -> hybrid_search()
"""
from typing import List, Optional

from src.embeddings.jina_embedder import JinaEmbedder
from src.search.index_manager import INDEX_NAME
from src.search.opensearch_client import get_opensearch_client
from src.utils.metrics import timed_stage

_embedder = JinaEmbedder()


def match_search(query: str, field: str = "chunk_text", top_k: int = 10) -> List[dict]:
    """Simple single-field match query."""
    client = get_opensearch_client()
    body = {"size": top_k, "query": {"match": {field: query}}, "_source": {"excludes": ["embedding"]}}
    resp = client.search(index=INDEX_NAME, body=body)
    return [{"score": h["_score"], **h["_source"]} for h in resp["hits"]["hits"]]


def boosting_search(query: str, demote_terms: List[str], top_k: int = 10) -> List[dict]:
    """Boosting query: promote docs matching `query`, demote docs matching `demote_terms`."""
    client = get_opensearch_client()
    body = {
        "size": top_k,
        "query": {
            "boosting": {
                "positive": {"multi_match": {"query": query, "fields": ["title^3", "summary^2", "chunk_text"]}},
                "negative": {"multi_match": {"query": " ".join(demote_terms), "fields": ["chunk_text"]}},
                "negative_boost": 0.3,
            }
        },
        "_source": {"excludes": ["embedding"]},
    }
    resp = client.search(index=INDEX_NAME, body=body)
    return [{"score": h["_score"], **h["_source"]} for h in resp["hits"]["hits"]]


def filtered_search(
    query: str,
    categories: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    top_k: int = 10,
) -> List[dict]:
    """Filter query: exact-match filters combined with relevance scoring (filters don't affect score)."""
    client = get_opensearch_client()
    filters = []
    if categories:
        filters.append({"terms": {"categories": categories}})
    if date_from or date_to:
        rng = {}
        if date_from:
            rng["gte"] = date_from
        if date_to:
            rng["lte"] = date_to
        filters.append({"range": {"published": rng}})

    body = {
        "size": top_k,
        "query": {
            "bool": {
                "must": {"multi_match": {"query": query, "fields": ["title^3", "summary^2", "chunk_text"]}},
                "filter": filters,
            }
        },
        "_source": {"excludes": ["embedding"]},
    }
    resp = client.search(index=INDEX_NAME, body=body)
    return [{"score": h["_score"], **h["_source"]} for h in resp["hits"]["hits"]]


def sorted_search(query: str, sort_by: str = "published", order: str = "desc", top_k: int = 10) -> List[dict]:
    """Sorting query: relevance-filtered results re-ordered by a field (e.g. recency)."""
    client = get_opensearch_client()
    body = {
        "size": top_k,
        "query": {"multi_match": {"query": query, "fields": ["title^3", "summary^2", "chunk_text"]}},
        "sort": [{sort_by: {"order": order}}, "_score"],
        "_source": {"excludes": ["embedding"]},
    }
    resp = client.search(index=INDEX_NAME, body=body)
    return [{"score": h["_score"], **h["_source"]} for h in resp["hits"]["hits"]]


def vector_search(query: str, top_k: int = 10) -> List[dict]:
    """Pure kNN semantic search using Jina query embeddings."""
    client = get_opensearch_client()
    query_vector = _embedder.embed_query(query)
    body = {
        "size": top_k,
        "query": {"knn": {"embedding": {"vector": query_vector, "k": top_k}}},
        "_source": {"excludes": ["embedding"]},
    }
    with timed_stage("vector_search"):
        resp = client.search(index=INDEX_NAME, body=body)
    return [{"score": h["_score"], **h["_source"]} for h in resp["hits"]["hits"]]


def hybrid_search(
    query: str,
    top_k: int = 10,
    bm25_weight: float = 0.5,
    vector_weight: float = 0.5,
    categories: Optional[List[str]] = None,
) -> List[dict]:
    """
    Hybrid = BM25 (multi_match) + kNN vector, fused client-side via
    normalized-score weighted sum (works on any OpenSearch version;
    doesn't require the paid Neural Search plugin's built-in hybrid pipeline).
    """
    from src.search.bm25_search import bm25_search as _bm25

    with timed_stage("hybrid_search"):
        bm25_hits = _bm25(query, top_k=top_k * 3, categories=categories)
        vector_hits = vector_search(query, top_k=top_k * 3)

    def normalize(hits):
        if not hits:
            return {}
        scores = [h["score"] for h in hits]
        lo, hi = min(scores), max(scores)
        span = (hi - lo) or 1.0
        return {h["arxiv_id"] + str(h.get("chunk_index", 0)): (h["score"] - lo) / span for h in hits}

    bm25_norm = normalize(bm25_hits)
    vector_norm = normalize(vector_hits)
    by_id = {h["arxiv_id"] + str(h.get("chunk_index", 0)): h for h in bm25_hits + vector_hits}

    fused_scores = {}
    for key in by_id:
        fused_scores[key] = bm25_weight * bm25_norm.get(key, 0.0) + vector_weight * vector_norm.get(key, 0.0)

    ranked = sorted(by_id.items(), key=lambda kv: fused_scores[kv[0]], reverse=True)[:top_k]
    return [{**doc, "score": fused_scores[key]} for key, doc in ranked]
