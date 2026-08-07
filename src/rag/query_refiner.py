"""Query Refinement: rewrites vague queries for better retrieval, with reasoning trace."""
from dataclasses import dataclass

from src.rag.llm_gemini import refine_query


@dataclass
class RefinementResult:
    original: str
    refined: str
    reasoning: str


def refine(query: str) -> RefinementResult:
    refined = refine_query(query)
    changed = refined.strip().lower() != query.strip().lower()
    reasoning = (
        f"Rewrote '{query}' -> '{refined}' for higher retrieval precision."
        if changed else "Query was already specific; no rewrite needed."
    )
    return RefinementResult(original=query, refined=refined if changed else query, reasoning=reasoning)
