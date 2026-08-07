"""Document Grading: filters retrieved chunks down to ones an LLM judges actually relevant."""
from dataclasses import dataclass
from typing import List

from src.rag.llm_gemini import grade_document
from src.utils.logging_config import logger


@dataclass
class GradedDoc:
    doc: dict
    relevant: bool


def grade_documents(query: str, docs: List[dict]) -> List[dict]:
    """Returns only the subset of `docs` graded relevant. Falls back to top-3 if all rejected."""
    graded = [GradedDoc(doc=d, relevant=grade_document(query, d.get("chunk_text", ""))) for d in docs]
    relevant = [g.doc for g in graded if g.relevant]

    if not relevant:
        logger.warning("Document grading rejected all candidates; falling back to top-3 by score.")
        relevant = docs[:3]

    logger.info(f"Document grading kept {len(relevant)}/{len(docs)} chunks")
    return relevant
