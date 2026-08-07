"""
Feature 9: Index Management
Creates/manages the `arxiv-papers` index with mappings tuned for:
  - BM25 full-text search (`text` fields with english analyzer)
  - kNN vector search over Jina embeddings (`knn_vector`)
  - exact filtering/sorting (`keyword` and `date` sub-fields)
"""
from config.settings import settings
from src.search.opensearch_client import get_opensearch_client
from src.utils.logging_config import logger

INDEX_NAME = settings.opensearch_index

INDEX_BODY = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "knn": True,
        },
        "analysis": {
            "analyzer": {
                "arxiv_text_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop", "porter_stem"],
                }
            }
        },
    },
    "mappings": {
        "properties": {
            "arxiv_id": {"type": "keyword"},
            "title": {
                "type": "text",
                "analyzer": "arxiv_text_analyzer",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 512}},
            },
            "summary": {"type": "text", "analyzer": "arxiv_text_analyzer"},
            "chunk_text": {"type": "text", "analyzer": "arxiv_text_analyzer"},
            "section_heading": {"type": "keyword"},
            "chunk_index": {"type": "integer"},
            "authors": {"type": "keyword"},
            "categories": {"type": "keyword"},
            "primary_category": {"type": "keyword"},
            "published": {"type": "date"},
            "updated": {"type": "date"},
            "citation_count": {"type": "integer"},  # optional boosting signal
            "embedding": {
                "type": "knn_vector",
                "dimension": settings.jina_embedding_dim,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "lucene",
                    "parameters": {"ef_construction": 128, "m": 24},
                },
            },
        }
    },
}


def create_index(force_recreate: bool = False) -> None:
    client = get_opensearch_client()
    exists = client.indices.exists(index=INDEX_NAME)

    if exists and force_recreate:
        client.indices.delete(index=INDEX_NAME)
        logger.warning(f"Deleted existing index '{INDEX_NAME}' for recreation")
        exists = False

    if not exists:
        client.indices.create(index=INDEX_NAME, body=INDEX_BODY)
        logger.info(f"Created index '{INDEX_NAME}'")
    else:
        logger.info(f"Index '{INDEX_NAME}' already exists")


def delete_index() -> None:
    client = get_opensearch_client()
    if client.indices.exists(index=INDEX_NAME):
        client.indices.delete(index=INDEX_NAME)
        logger.warning(f"Deleted index '{INDEX_NAME}'")


if __name__ == "__main__":
    create_index()
