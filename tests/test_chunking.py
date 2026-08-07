"""Unit test for section-based chunking -- runs with no external services."""
from src.chunking.section_chunker import SectionChunker
from src.ingestion.models import ParsedPaper, Section


def test_chunk_respects_overlap():
    long_text = " ".join([f"word{i}" for i in range(1000)])
    parsed = ParsedPaper(
        arxiv_id="2501.00001",
        full_text=long_text,
        sections=[Section(heading="Introduction", level=1, text=long_text)],
    )
    chunker = SectionChunker(max_tokens=100, overlap_tokens=20)
    chunks = chunker.chunk(parsed)

    assert len(chunks) > 1
    # consecutive chunks should share some overlapping words
    first_words = set(chunks[0].text.split())
    second_words = set(chunks[1].text.split())
    assert first_words & second_words, "Expected overlapping words between consecutive chunks"


def test_chunk_to_dicts_shape():
    parsed = ParsedPaper(
        arxiv_id="2501.00002",
        full_text="short text",
        sections=[Section(heading="Abstract", level=1, text="short text")],
    )
    chunker = SectionChunker()
    dicts = chunker.chunk_to_dicts(parsed)
    assert dicts[0].keys() == {"chunk_index", "section_heading", "text", "token_count"}
