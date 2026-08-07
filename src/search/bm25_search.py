"""Feature 10: BM25 Search -- full-text relevance search over chunk_text/title/summary."""
from typing import List, Optional

from src.search.index_manager import INDEX_NAME
from src.search.opensearch_client import get_opensearch_client
from src.utils.metrics import timed_stage


def bm25_search(
    query: str,
    top_k: int = 10,
    categories: Optional[List[str]] = None,
) -> List[dict]:
    """Multi-match BM25 query across title (boosted), summary, and chunk_text."""
    client = get_opensearch_client()

    must_clauses = [{
        "multi_match": {
            "query": query,
            "fields": ["title^3", "summary^2", "chunk_text"],
            "type": "best_fields",
            "fuzziness": "AUTO",
        }
    }]
    filters = [{"terms": {"categories": categories}}] if categories else []

    body = {
        "size": top_k,
        "query": {"bool": {"must": must_clauses, "filter": filters}},
        "_source": {"excludes": ["embedding"]},
    }

    with timed_stage("bm25_search"):
        resp = client.search(index=INDEX_NAME, body=body)

    return [
        {"score": h["_score"], **h["_source"]}
        for h in resp["hits"]["hits"]
    ]
