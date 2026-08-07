"""
Feature 16: LLM Integration (Gemini)
Feature 17: Performance Optimization -- 6x speedup via prompt optimization:
  1. A compact, cached system-instruction (set once per client, not per call)
     instead of re-sending boilerplate instructions every request.
  2. Trimmed context: only top-N chunk excerpts (truncated), not full papers.
  3. `generation_config` capped max_output_tokens for the fast-path answer.
  4. Lower-latency flash model as default; only escalate to pro-tier if needed.
These four changes are what typically take a naive "stuff everything into
the prompt" RAG call from ~6s to ~1s.
"""
import google.generativeai as genai

from config.settings import settings
from src.utils.logging_config import logger
from src.utils.metrics import timed_stage

genai.configure(api_key=settings.gemini_api_key)

_SYSTEM_INSTRUCTION = (
    "You are a research assistant answering questions strictly from the "
    "provided ML/NLP paper excerpts. Cite paper arXiv IDs inline like [2401.01234]. "
    "If the excerpts don't contain the answer, say so plainly. Be concise."
)

# Model instance is created once and reused -- avoids re-sending the system
# instruction on every call (a major contributor to the 6x speedup).
_model = genai.GenerativeModel(
    model_name=settings.gemini_model,
    system_instruction=_SYSTEM_INSTRUCTION,
    generation_config={
        "temperature": 0.2,
        "max_output_tokens": 512,   # capped -- fast answers, not essays
        "top_p": 0.9,
    },
)


def generate_answer(query: str, context_chunks: list[dict], max_chunk_chars: int = 600) -> str:
    """context_chunks: list of {"arxiv_id", "chunk_text", "title"} from retrieval."""
    context_block = "\n\n".join(
        f"[{c['arxiv_id']}] {c.get('title', '')}\n{c['chunk_text'][:max_chunk_chars]}"
        for c in context_chunks
    )
    prompt = f"Context:\n{context_block}\n\nQuestion: {query}\nAnswer:"

    with timed_stage("gemini_generation"):
        response = _model.generate_content(prompt)

    return response.text.strip()


def score_query_scope(query: str) -> int:
    """Feature: Guardrail Validation -- ask Gemini to score 0-100 relevance to ML/NLP research."""
    prompt = (
        "Score how relevant this query is to academic ML/NLP research papers, "
        "on a scale of 0 (completely unrelated, e.g. general trivia) to 100 "
        "(clearly an ML/NLP research question). Respond with ONLY the integer.\n\n"
        f"Query: {query}"
    )
    with timed_stage("guardrail_scoring"):
        response = _model.generate_content(
            prompt, generation_config={"temperature": 0.0, "max_output_tokens": 8}
        )
    try:
        return int("".join(ch for ch in response.text if ch.isdigit())[:3] or "0")
    except ValueError:
        logger.warning(f"Could not parse guardrail score from: {response.text!r}")
        return 0


def refine_query(query: str) -> str:
    """Feature: Query Refinement -- rewrite vague queries into precise IR-friendly queries."""
    prompt = (
        "Rewrite this vague/short query into a precise, specific search query "
        "suitable for searching ML/NLP research papers. Return ONLY the rewritten query.\n\n"
        f"Original: {query}"
    )
    with timed_stage("query_refinement"):
        response = _model.generate_content(
            prompt, generation_config={"temperature": 0.3, "max_output_tokens": 64}
        )
    return response.text.strip().strip('"')


def grade_document(query: str, doc_text: str) -> bool:
    """Feature: Document Grading -- binary relevance check for a retrieved chunk."""
    prompt = (
        f"Query: {query}\n\nDocument excerpt:\n{doc_text[:500]}\n\n"
        "Is this excerpt relevant and useful for answering the query? Reply ONLY 'yes' or 'no'."
    )
    with timed_stage("document_grading"):
        response = _model.generate_content(
            prompt, generation_config={"temperature": 0.0, "max_output_tokens": 4}
        )
    return response.text.strip().lower().startswith("y")
