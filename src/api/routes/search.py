"""Feature 22: Search API -- exposes every search mode as a REST endpoint."""
from typing import List, Optional

from fastapi import APIRouter, Query

from src.search.bm25_search import bm25_search
from src.search.hybrid_search import (
    match_search, boosting_search, filtered_search, sorted_search,
    vector_search, hybrid_search,
)

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/bm25")
def search_bm25(q: str, top_k: int = 10, categories: Optional[List[str]] = Query(None)):
    return {"mode": "bm25", "results": bm25_search(q, top_k=top_k, categories=categories)}


@router.get("/match")
def search_match(q: str, field: str = "chunk_text", top_k: int = 10):
    return {"mode": "match", "results": match_search(q, field=field, top_k=top_k)}


@router.get("/vector")
def search_vector(q: str, top_k: int = 10):
    return {"mode": "vector", "results": vector_search(q, top_k=top_k)}


@router.get("/hybrid")
def search_hybrid(q: str, top_k: int = 10, bm25_weight: float = 0.5, vector_weight: float = 0.5):
    return {
        "mode": "hybrid",
        "results": hybrid_search(q, top_k=top_k, bm25_weight=bm25_weight, vector_weight=vector_weight),
    }


@router.get("/filtered")
def search_filtered(
    q: str,
    categories: Optional[List[str]] = Query(None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    top_k: int = 10,
):
    return {
        "mode": "filtered",
        "results": filtered_search(q, categories=categories, date_from=date_from, date_to=date_to, top_k=top_k),
    }


@router.get("/sorted")
def search_sorted(q: str, sort_by: str = "published", order: str = "desc", top_k: int = 10):
    return {"mode": "sorted", "results": sorted_search(q, sort_by=sort_by, order=order, top_k=top_k)}


@router.get("/boosting")
def search_boosting(q: str, demote: List[str] = Query(...), top_k: int = 10):
    return {"mode": "boosting", "results": boosting_search(q, demote_terms=demote, top_k=top_k)}
