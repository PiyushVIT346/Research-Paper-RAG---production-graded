"""
Feature 4: Database Integration -- connection/session management for Neon.
Uses a pooled SQLAlchemy engine; `pool_pre_ping` avoids stale-connection
errors that are common with serverless Postgres (Neon scales to zero).
"""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config.settings import settings
from src.db.models import Base
from src.utils.logging_config import logger

engine = create_engine(
    settings.neon_database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,  # recycle before Neon idles the connection out
)
#SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db():
    """Create tables if they don't exist. Run once at deploy time."""
    Base.metadata.create_all(bind=engine)
    logger.info("Neon database schema ensured (tables created if missing).")


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
