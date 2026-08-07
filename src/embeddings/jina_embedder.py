"""
Feature 13: Standalone Embedding Generation
Direct integration with the Jina AI embeddings API (no LangChain wrapper --
one HTTP call, fully under our control for batching/retry/rate limits).
"""
from typing import List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings
from src.utils.logging_config import logger
from src.utils.metrics import timed_stage, PIPELINE_ERRORS

JINA_EMBED_URL = "https://api.jina.ai/v1/embeddings"


class JinaEmbedder:
    def __init__(self, model: str = None, batch_size: int = 32):
        self.model = model or settings.jina_model
        self.batch_size = batch_size
        self._headers = {
            "Authorization": f"Bearer {settings.jina_api_key}",
            "Content-Type": "application/json",
        }

    @retry(reraise=True, stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=15))
    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        payload = {"model": self.model, "input": texts, "task": "retrieval.passage"}
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(JINA_EMBED_URL, headers=self._headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        # Jina returns items possibly out of order; sort by "index" to realign with input.
        ordered = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in ordered]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batches requests to respect Jina's per-request payload limits."""
        embeddings: List[List[float]] = []
        with timed_stage("jina_embedding"):
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                try:
                    embeddings.extend(self._embed_batch(batch))
                except Exception as e:
                    PIPELINE_ERRORS.labels(stage="embedding").inc()
                    logger.error(f"Jina embedding batch failed: {e}")
                    raise
        logger.info(f"Embedded {len(texts)} texts via Jina ({self.model})")
        return embeddings

    def embed_query(self, query: str) -> List[float]:
        payload = {"model": self.model, "input": [query], "task": "retrieval.query"}
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(JINA_EMBED_URL, headers=self._headers, json=payload)
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
