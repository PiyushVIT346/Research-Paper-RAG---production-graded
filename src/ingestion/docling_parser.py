"""
Lightweight PDF parser using pypdf instead of Docling.
Docling's layout model requires native compilation (MSVC/cl.exe) and heavy
memory on Windows, which isn't reliably available in this environment.
This trades structured section/table/figure detection for a simple,
dependency-light extractor. Keeps the same ParsedPaper interface so
nothing downstream (chunker, repository, pipeline) needs to change.
"""
from pathlib import Path

from pypdf import PdfReader

from src.ingestion.models import ParsedPaper, Section
from src.utils.logging_config import logger
from src.utils.metrics import PIPELINE_ERRORS, timed_stage


class DoclingParser:
    """Class name kept as DoclingParser so pipeline.py needs zero changes."""

    def parse(self, arxiv_id: str, pdf_path: Path) -> ParsedPaper:
        with timed_stage("pdf_parse"):
            try:
                reader = PdfReader(str(pdf_path))
                page_texts = [page.extract_text() or "" for page in reader.pages]
            except Exception as e:
                PIPELINE_ERRORS.labels(stage="pdf_parse").inc()
                logger.error(f"pypdf failed to parse {arxiv_id}: {e}")
                raise

        # Postgres text columns reject NUL bytes -- pypdf occasionally emits them.
        full_text = "\n\n".join(page_texts).replace("\x00", "")
        sections = [Section(heading="Full Text", level=1, text=full_text)]

        logger.info(
            f"Parsed {arxiv_id}: {len(reader.pages)} pages, {len(full_text)} chars "
            f"(pypdf -- no OCR/tables/figures)"
        )
        return ParsedPaper(arxiv_id=arxiv_id, full_text=full_text, sections=sections, tables=[], figures=[])