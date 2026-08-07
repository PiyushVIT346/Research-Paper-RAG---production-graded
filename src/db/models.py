"""Feature 4: Database Integration -- ORM models for Neon PostgreSQL."""
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, DateTime, Integer, ForeignKey, JSON, Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Paper(Base):
    __tablename__ = "papers"

    arxiv_id = Column(String(32), primary_key=True)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    authors = Column(JSON, nullable=False, default=list)
    categories = Column(JSON, nullable=False, default=list)
    primary_category = Column(String(32), index=True)
    published = Column(DateTime, nullable=False)
    updated = Column(DateTime, nullable=False)
    pdf_url = Column(Text, nullable=False)
    doi = Column(String(128), nullable=True)
    journal_ref = Column(Text, nullable=True)

    full_text = Column(Text, nullable=True)          # from Docling
    parsed_at = Column(DateTime, nullable=True)
    ingestion_status = Column(String(32), default="fetched", index=True)
    # fetched -> pdf_downloaded -> parsed -> chunked -> embedded -> indexed -> failed

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sections = relationship("PaperSection", back_populates="paper", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="paper", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_papers_status_category", "ingestion_status", "primary_category"),)


class PaperSection(Base):
    __tablename__ = "paper_sections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    arxiv_id = Column(String(32), ForeignKey("papers.arxiv_id", ondelete="CASCADE"), index=True)
    heading = Column(Text, nullable=False)
    level = Column(Integer, default=1)
    text = Column(Text, nullable=False)
    order_index = Column(Integer, default=0)

    paper = relationship("Paper", back_populates="sections")


class Chunk(Base):
    """Feature 12: section-based chunks with overlap, ready for embedding."""
    __tablename__ = "chunks"

    id = Column(String(64), primary_key=True)  # f"{arxiv_id}::{chunk_index}"
    arxiv_id = Column(String(32), ForeignKey("papers.arxiv_id", ondelete="CASCADE"), index=True)
    chunk_index = Column(Integer, nullable=False)
    section_heading = Column(Text, nullable=True)
    text = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    embedding_model = Column(String(64), nullable=True)
    embedded_at = Column(DateTime, nullable=True)

    paper = relationship("Paper", back_populates="chunks")

    __table_args__ = (Index("ix_chunks_arxiv_id_idx", "arxiv_id", "chunk_index"),)
