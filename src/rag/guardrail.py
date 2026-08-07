"""
Guardrail Validation: LLM scores query scope 0-100 before any retrieval happens.
Score < GUARDRAIL_SCORE_THRESHOLD (default 60) => reject as out-of-scope.
"""
from dataclasses import dataclass

from config.settings import settings
from src.rag.llm_gemini import score_query_scope
from src.utils.logging_config import logger
from src.utils.metrics import GUARDRAIL_REJECTIONS


@dataclass
class GuardrailResult:
    score: int
    in_scope: bool
    reasoning: str


def validate_query_scope(query: str) -> GuardrailResult:
    score = score_query_scope(query)
    in_scope = score >= settings.guardrail_score_threshold

    if not in_scope:
        GUARDRAIL_REJECTIONS.inc()
        logger.info(f"Guardrail rejected query (score={score}): {query!r}")

    reasoning = (
        f"Scored {score}/100 for ML/NLP research relevance "
        f"(threshold={settings.guardrail_score_threshold}). "
        f"{'Within scope.' if in_scope else 'Out of scope -- rejecting before retrieval.'}"
    )
    return GuardrailResult(score=score, in_scope=in_scope, reasoning=reasoning)
