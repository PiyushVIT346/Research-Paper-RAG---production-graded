"""
The RAG Agent: orchestrates the full agentic flow requested:

  1. Guardrail Validation      -- score query 0-100, reject if < threshold
  2. Query Refinement          -- rewrite vague queries
  3. Retrieval (hybrid search) -- BM25 + vector fusion
  4. Document Grading          -- LLM filters irrelevant retrieved chunks
  5. Iterative Improvement     -- if grading leaves too little, refine again
     and retry (max `settings.max_rag_retries` attempts)
  6. Answer Generation         -- Gemini, with prompt-optimization (6x faster)
  7. Redis caching             -- sub-second responses on cache hit
  8. LangFuse tracing          -- every stage recorded
  9. Reasoning Transparency    -- every stage's reasoning returned to caller
"""
import time
from dataclasses import dataclass, field
from typing import List, Optional

from config.settings import settings
from src.rag.cache import get_cached_response, set_cached_response
from src.rag.document_grader import grade_documents
from src.rag.guardrail import validate_query_scope
from src.rag.llm_gemini import generate_answer
from src.rag.query_refiner import refine
from src.rag.tracing import RagTrace
from src.search.hybrid_search import hybrid_search
from src.utils.logging_config import logger


@dataclass
class RagResponse:
    query: str
    answer: Optional[str]
    sources: List[dict] = field(default_factory=list)
    reasoning_steps: List[str] = field(default_factory=list)
    guardrail_score: int = 0
    in_scope: bool = True
    attempts: int = 1
    cached: bool = False
    latency_seconds: float = 0.0


MIN_RELEVANT_DOCS = 2  # if grading keeps fewer than this, retry with a refined query


def run_rag_query(query: str, mode: str = "hybrid", top_k: int = 5) -> RagResponse:
    start = time.perf_counter()
    reasoning: List[str] = []

    # ---- Cache check first: sub-second path for repeated queries ----
    cached = get_cached_response(query, mode)
    if cached:
        cached["cached"] = True
        cached["latency_seconds"] = round(time.perf_counter() - start, 4)
        return RagResponse(**cached)

    trace = RagTrace(query)

    # ---- 1. Guardrail validation ----
    with trace.span("guardrail"):
        guard = validate_query_scope(query)
    reasoning.append(guard.reasoning)

    if not guard.in_scope:
        response = RagResponse(
            query=query, answer=None, reasoning_steps=reasoning,
            guardrail_score=guard.score, in_scope=False,
            latency_seconds=round(time.perf_counter() - start, 4),
        )
        trace.log_output({"rejected": True, "score": guard.score})
        trace.flush()
        return response

    # ---- 2-5. Refine -> retrieve -> grade, retrying up to max_rag_retries ----
    current_query = query
    graded_docs: List[dict] = []
    attempts = 0

    while attempts < settings.max_rag_retries + 1:
        attempts += 1
        with trace.span("refine", attempt=attempts):
            refinement = refine(current_query)
        reasoning.append(f"[attempt {attempts}] {refinement.reasoning}")
        current_query = refinement.refined

        with trace.span("retrieve", attempt=attempts, mode=mode):
            raw_docs = hybrid_search(current_query, top_k=top_k)
        reasoning.append(f"[attempt {attempts}] Retrieved {len(raw_docs)} candidate chunks via {mode} search.")

        with trace.span("grade", attempt=attempts):
            graded_docs = grade_documents(current_query, raw_docs)
        reasoning.append(f"[attempt {attempts}] Document grading kept {len(graded_docs)} relevant chunk(s).")

        if len(graded_docs) >= MIN_RELEVANT_DOCS or attempts > settings.max_rag_retries:
            break
        reasoning.append(f"[attempt {attempts}] Too few relevant docs -- retrying with a refined query.")

    # ---- 6. Generate answer ----
    with trace.span("generate"):
        answer = generate_answer(current_query, graded_docs)
    reasoning.append("Generated answer from graded context using Gemini (prompt-optimized fast path).")

    response = RagResponse(
        query=query,
        answer=answer,
        sources=[{"arxiv_id": d["arxiv_id"], "title": d.get("title"), "score": d.get("score")} for d in graded_docs],
        reasoning_steps=reasoning,
        guardrail_score=guard.score,
        in_scope=True,
        attempts=attempts,
        cached=False,
        latency_seconds=round(time.perf_counter() - start, 4),
    )

    trace.log_output({"answer": answer, "sources": response.sources})
    trace.flush()

    # ---- 7. Cache the response for next time ----
    set_cached_response(query, mode, response.__dict__)

    logger.info(f"RAG query completed in {response.latency_seconds}s (attempts={attempts})")
    return response
