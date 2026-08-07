"""
FastAPI application entrypoint.
Run locally (no Docker):  uvicorn src.api.main:app --reload --port 8000
"""
import time

from fastapi import FastAPI, Request

from src.api.routes import health, ingestion, search, rag
from src.utils.logging_config import logger

app = FastAPI(
    title="arXiv Advanced RAG System",
    description="Production-grade RAG over cs.AI research papers.",
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(ingestion.router)
app.include_router(search.router)
app.include_router(rag.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration*1000:.1f}ms)")
    return response


@app.get("/")
def root():
    return {"service": "arxiv-rag-system", "docs": "/docs"}
