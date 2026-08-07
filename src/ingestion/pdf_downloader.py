"""
Feature 2: PDF Download System
Downloads arXiv PDFs to a local cache directory (plain filesystem, no
Docker volumes needed), with retry/backoff and integrity checks so a
half-written file never poisons the cache.
"""
import hashlib
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import settings
from src.utils.logging_config import logger
from src.utils.metrics import PIPELINE_ERRORS


class PDFDownloadError(Exception):
    pass


class PDFDownloader:
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir or settings.pdf_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, arxiv_id: str) -> Path:
        safe_id = arxiv_id.replace("/", "_")
        return self.cache_dir / f"{safe_id}.pdf"

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type((httpx.HTTPError, PDFDownloadError)),
    )
    def download(self, arxiv_id: str, pdf_url: str, force: bool = False) -> Path:
        """
        Downloads a PDF, using the local cache when possible.
        Writes to a .part temp file first, then atomically renames --
        guarantees the cache never contains a truncated file.
        """
        dest = self._cache_path(arxiv_id)
        if dest.exists() and not force:
            logger.debug(f"Cache hit for {arxiv_id}")
            return dest

        tmp_path = dest.with_suffix(".part")
        try:
            with httpx.stream("GET", pdf_url, timeout=30.0, follow_redirects=True) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                if "pdf" not in content_type and "octet-stream" not in content_type:
                    raise PDFDownloadError(f"Unexpected content-type '{content_type}' for {arxiv_id}")

                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=1 << 16):
                        f.write(chunk)

            if tmp_path.stat().st_size == 0:
                raise PDFDownloadError(f"Downloaded empty file for {arxiv_id}")

            tmp_path.rename(dest)
            logger.info(f"Downloaded {arxiv_id} -> {dest} ({dest.stat().st_size / 1024:.1f} KB)")
            return dest

        except Exception as e:
            PIPELINE_ERRORS.labels(stage="pdf_download").inc()
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            logger.error(f"Failed to download {arxiv_id}: {e}")
            raise

    def is_cached(self, arxiv_id: str) -> bool:
        return self._cache_path(arxiv_id).exists()
