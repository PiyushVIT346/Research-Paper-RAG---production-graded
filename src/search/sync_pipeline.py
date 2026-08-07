"""
Feature 11: Data Pipeline
Transfers chunked+embedded papers from PostgreSQL (source of truth) into
OpenSearch (search index), one document per chunk so BM25/vector search
operate at chunk granularity while still carrying paper-level metadata.
"""
from opensearchpy.helpers import bulk

from src.db.repository import PaperRepository
from src.embeddings.jina_embedder import JinaEmbedder
from src.search.index_manager import INDEX_NAME
from src.search.opensearch_client import get_opensearch_client
from src.utils.logging_config import logger
from src.utils.metrics import timed_stage, PIPELINE_ERRORS

_embedder = JinaEmbedder()


def sync_paper_to_opensearch(arxiv_id: str) -> int:
    """Embeds (if needed) and indexes all chunks for one paper. Returns #docs indexed."""
    paper = PaperRepository.get_paper(arxiv_id)
    if paper is None:
        logger.warning(f"sync: paper {arxiv_id} not found")
        return 0

    chunks = PaperRepository.get_chunks(arxiv_id)
    if not chunks:
        logger.warning(f"sync: no chunks for {arxiv_id}, skipping")
        return 0

    with timed_stage("opensearch_sync"):
        texts = [c.text for c in chunks]
        try:
            vectors = _embedder.embed_texts(texts)
        except Exception as e:
            PIPELINE_ERRORS.labels(stage="sync_embedding").inc()
            logger.error(f"Embedding failed for {arxiv_id}: {e}")
            raise

        client = get_opensearch_client()
        actions = []
        for chunk, vector in zip(chunks, vectors):
            actions.append({
                "_index": INDEX_NAME,
                "_id": chunk.id,
                "_source": {
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "summary": paper.summary,
                    "chunk_text": chunk.text,
                    "section_heading": chunk.section_heading,
                    "chunk_index": chunk.chunk_index,
                    "authors": paper.authors,
                    "categories": paper.categories,
                    "primary_category": paper.primary_category,
                    "published": paper.published.isoformat() if paper.published else None,
                    "updated": paper.updated.isoformat() if paper.updated else None,
                    "embedding": vector,
                },
            })
        success, errors = bulk(client, actions, raise_on_error=False)
        if errors:
            logger.error(f"OpenSearch bulk had {len(errors)} errors for {arxiv_id}: {errors[:3]}")

    PaperRepository.mark_status(arxiv_id, "indexed")
    logger.info(f"Indexed {success} chunks for {arxiv_id} into OpenSearch")
    return success


def sync_all_pending(limit: int = 100) -> dict:
    """Batch-sync everything that's chunked but not yet indexed."""
    papers = PaperRepository.all_papers_for_sync(limit=limit)
    total_indexed, failed = 0, []
    for p in papers:
        if p.ingestion_status == "indexed":
            continue
        try:
            total_indexed += sync_paper_to_opensearch(p.arxiv_id)
        except Exception:
            failed.append(p.arxiv_id)
    return {"papers_processed": len(papers), "chunks_indexed": total_indexed, "failed": failed}


if __name__ == "__main__":
    print(sync_all_pending())
