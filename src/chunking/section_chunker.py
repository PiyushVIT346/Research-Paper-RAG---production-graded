"""
Feature 12: Section-Based Chunking
Chunks text within Docling-extracted sections (so a chunk never straddles
two unrelated sections), using a sliding window with configurable overlap
so retrieval doesn't lose context at chunk boundaries.
"""
from dataclasses import dataclass
from typing import List

from src.ingestion.models import ParsedPaper


@dataclass
class ChunkResult:
    chunk_index: int
    section_heading: str
    text: str
    token_count: int


def _approx_token_count(text: str) -> int:
    # Fast heuristic (~4 chars/token) avoids a tokenizer dependency in the hot path.
    return max(1, len(text) // 4)


def _split_words(text: str, max_tokens: int, overlap_tokens: int) -> List[str]:
    words = text.split()
    max_words = max_tokens * 4 // 5  # rough words-per-token(~0.8) inverse for word-count budget
    overlap_words = overlap_tokens * 4 // 5
    if len(words) <= max_words:
        return [text] if text.strip() else []

    chunks, start = [], 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap_words  # slide back for overlap
    return chunks


class SectionChunker:
    def __init__(self, max_tokens: int = 400, overlap_tokens: int = 60):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, parsed: ParsedPaper) -> List[ChunkResult]:
        results: List[ChunkResult] = []
        idx = 0
        sections = parsed.sections or [type("S", (), {"heading": "Full Text", "text": parsed.full_text})()]

        for sec in sections:
            for piece in _split_words(sec.text, self.max_tokens, self.overlap_tokens):
                if not piece.strip():
                    continue
                results.append(ChunkResult(
                    chunk_index=idx,
                    section_heading=sec.heading,
                    text=piece,
                    token_count=_approx_token_count(piece),
                ))
                idx += 1

        return results

    def chunk_to_dicts(self, parsed: ParsedPaper) -> List[dict]:
        return [
            {
                "chunk_index": c.chunk_index,
                "section_heading": c.section_heading,
                "text": c.text,
                "token_count": c.token_count,
            }
            for c in self.chunk(parsed)
        ]
