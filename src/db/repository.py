"""Feature 4: Database Integration -- repository (CRUD) layer, keeps SQL out of business logic."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.connection import get_session
from src.db.models import Paper, PaperSection, Chunk
from src.ingestion.arxiv_client import ArxivPaper
from src.ingestion.models import ParsedPaper
from src.utils.logging_config import logger


class PaperRepository:

    @staticmethod
    def upsert_from_arxiv(paper: ArxivPaper) -> None:
        """Idempotent insert: re-fetching the same arxiv_id updates metadata, never duplicates."""
        with get_session() as s:
            stmt = pg_insert(Paper).values(
                arxiv_id=paper.arxiv_id,
                title=paper.title,
                summary=paper.summary,
                authors=paper.authors,
                categories=paper.categories,
                primary_category=paper.primary_category,
                published=paper.published,
                updated=paper.updated,
                pdf_url=paper.pdf_url,
                doi=paper.doi,
                journal_ref=paper.journal_ref,
                ingestion_status="fetched",
            ).on_conflict_do_update(
                index_elements=["arxiv_id"],
                set_=dict(
                    title=paper.title,
                    summary=paper.summary,
                    updated=paper.updated,
                    updated_at=datetime.utcnow(),
                ),
            )
            s.execute(stmt)

    @staticmethod
    def save_parsed_content(parsed: ParsedPaper) -> None:
        with get_session() as s:
            s.query(PaperSection).filter(PaperSection.arxiv_id == parsed.arxiv_id).delete()
            for idx, sec in enumerate(parsed.sections):
                s.add(PaperSection(
                    arxiv_id=parsed.arxiv_id, heading=sec.heading,
                    level=sec.level, text=sec.text, order_index=idx,
                ))
            paper = s.get(Paper, parsed.arxiv_id)
            if paper:
                paper.full_text = parsed.full_text
                paper.parsed_at = datetime.utcnow()
                paper.ingestion_status = "parsed"

    @staticmethod
    def save_chunks(arxiv_id: str, chunks: List[dict]) -> None:
        """`chunks` = [{"chunk_index", "section_heading", "text", "token_count"}, ...]"""
        with get_session() as s:
            s.query(Chunk).filter(Chunk.arxiv_id == arxiv_id).delete()
            for c in chunks:
                s.add(Chunk(
                    id=f"{arxiv_id}::{c['chunk_index']}",
                    arxiv_id=arxiv_id,
                    chunk_index=c["chunk_index"],
                    section_heading=c.get("section_heading"),
                    text=c["text"],
                    token_count=c.get("token_count"),
                ))
            paper = s.get(Paper, arxiv_id)
            if paper:
                paper.ingestion_status = "chunked"

    @staticmethod
    def mark_status(arxiv_id: str, status: str) -> None:
        with get_session() as s:
            paper = s.get(Paper, arxiv_id)
            if paper:
                paper.ingestion_status = status

    @staticmethod
    def get_paper(arxiv_id: str) -> Optional[Paper]:
        with get_session() as s:
            return s.get(Paper, arxiv_id)

    @staticmethod
    def list_by_status(status: str, limit: int = 100) -> List[Paper]:
        with get_session() as s:
            return s.execute(
                select(Paper).where(Paper.ingestion_status == status).limit(limit)
            ).scalars().all()

    @staticmethod
    def get_chunks(arxiv_id: str) -> List[Chunk]:
        with get_session() as s:
            return s.execute(
                select(Chunk).where(Chunk.arxiv_id == arxiv_id).order_by(Chunk.chunk_index)
            ).scalars().all()

    @staticmethod
    def all_papers_for_sync(limit: int = 500) -> List[Paper]:
        """Used by the Postgres -> OpenSearch sync pipeline (Feature 11)."""
        with get_session() as s:
            return s.execute(
                select(Paper).where(Paper.ingestion_status.in_(["chunked", "embedded", "indexed"])).limit(limit)
            ).scalars().all()
