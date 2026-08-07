"""
Feature 19: LangFuse Observability (SDK v4, OpenTelemetry-based).
Every Langfuse call is wrapped in try/except so tracing issues never take
down the actual RAG request -- observability should never be on the
critical path of correctness.
"""
from contextlib import contextmanager

from langfuse import Langfuse

from config.settings import settings
from src.utils.logging_config import logger

_langfuse = None
if settings.langfuse_public_key and settings.langfuse_secret_key:
    try:
        _langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception as e:
        logger.warning(f"LangFuse init failed, tracing disabled: {e}")
else:
    logger.warning("LangFuse keys not set -- tracing disabled (no-op mode).")


class RagTrace:
    def __init__(self, query: str):
        self.query = query
        self._root_span = None
        if _langfuse:
            try:
                self._root_span = _langfuse.span(name="rag_query", input={"query": query})
            except Exception as e:
                logger.warning(f"LangFuse start_span failed: {e}")

    @contextmanager
    def span(self, name: str, **metadata):
        s = None
        if self._root_span:
            try:
                s = self._root_span.start_span(name=name, metadata=metadata)
            except Exception as e:
                logger.warning(f"LangFuse child span failed: {e}")
        try:
            yield
            if s:
                s.end()
        except Exception:
            if s:
                try:
                    s.end()
                except Exception:
                    pass
            raise

    def log_output(self, output: dict):
        if self._root_span:
            try:
                self._root_span.update(output=output)
            except Exception as e:
                logger.warning(f"LangFuse update failed: {e}")

    def flush(self):
        if self._root_span:
            try:
                self._root_span.end()
            except Exception:
                pass
        if _langfuse:
            try:
                _langfuse.flush()
            except Exception:
                pass