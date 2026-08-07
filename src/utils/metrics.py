"""
Production metrics (feature 6, 20, 21): request latency, cache hit rate,
pipeline throughput. Exposed via /metrics using prometheus_client so any
scrape-based monitoring stack (Grafana/Prometheus) can consume it -- no
Docker needed, it's just an HTTP endpoint on the FastAPI app.
"""
import time
from contextlib import contextmanager
from prometheus_client import Counter, Histogram

REQUEST_LATENCY = Histogram(
    "rag_request_latency_seconds", "Latency of RAG pipeline stages", ["stage"]
)
CACHE_HITS = Counter("rag_cache_hits_total", "Redis cache hits")
CACHE_MISSES = Counter("rag_cache_misses_total", "Redis cache misses")
GUARDRAIL_REJECTIONS = Counter("rag_guardrail_rejections_total", "Out-of-scope queries rejected")
PIPELINE_PAPERS_PROCESSED = Counter("pipeline_papers_processed_total", "Papers ingested end-to-end")
PIPELINE_ERRORS = Counter("pipeline_errors_total", "Errors during ingestion pipeline", ["stage"])


@contextmanager
def timed_stage(stage: str):
    """Usage: `with timed_stage('embedding'): ...`  records latency automatically."""
    start = time.perf_counter()
    try:
        yield
    finally:
        REQUEST_LATENCY.labels(stage=stage).observe(time.perf_counter() - start)
