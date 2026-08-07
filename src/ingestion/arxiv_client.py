"""
Feature 1: arXiv API Client
Fetches cs.AI papers from the arXiv export API, respecting arXiv's
"one request per >=3 seconds" etiquette via a token-bucket-style sleep.
"""
import time
from dataclasses import dataclass, field
from typing import List, Optional

import arxiv

from config.settings import settings
from src.utils.logging_config import logger


@dataclass
class ArxivPaper:
    arxiv_id: str
    title: str
    summary: str
    authors: List[str]
    categories: List[str]
    published: str
    updated: str
    pdf_url: str
    primary_category: str
    doi: Optional[str] = None
    journal_ref: Optional[str] = None
    extra: dict = field(default_factory=dict)


class RateLimiter:
    """Simple blocking rate limiter: guarantees >= `min_interval` seconds between calls."""

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._last_call = 0.0

    def wait(self):
        elapsed = time.monotonic() - self._last_call
        remaining = self.min_interval - elapsed
        if remaining > 0:
            logger.debug(f"Rate limiter sleeping {remaining:.2f}s")
            time.sleep(remaining)
        self._last_call = time.monotonic()


class ArxivClient:
    """Thin, rate-limited wrapper around the `arxiv` python package."""

    def __init__(
        self,
        category: str = None,
        rate_limit_seconds: float = None,
        page_size: int = 50,
    ):
        self.category = category or settings.arxiv_category
        self.page_size = page_size
        self._limiter = RateLimiter(rate_limit_seconds or settings.arxiv_rate_limit_seconds)
        self._client = arxiv.Client(page_size=page_size, delay_seconds=0, num_retries=3)

    def fetch_recent(self, max_results: int = None, start_offset: int = 0) -> List[ArxivPaper]:
        """
        Fetch the most recent papers for the configured category.
        Rate limiting is applied per underlying HTTP page fetch, not per paper,
        since the arxiv library paginates internally -- we hook in via the
        generator so every page request goes through the limiter.
        """
        max_results = max_results or settings.arxiv_max_results
        search = arxiv.Search(
            query=f"cat:{self.category}",
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers: List[ArxivPaper] = []
        self._limiter.wait()  # first call
        try:
            for i, result in enumerate(self._client.results(search, offset=start_offset)):
                # arxiv lib batches pages internally; throttle every `page_size` results
                if i > 0 and i % self.page_size == 0:
                    self._limiter.wait()

                papers.append(
                    ArxivPaper(
                        arxiv_id=result.get_short_id(),
                        title=result.title.strip(),
                        summary=result.summary.strip().replace("\n", " "),
                        authors=[a.name for a in result.authors],
                        categories=result.categories,
                        published=result.published.isoformat(),
                        updated=result.updated.isoformat(),
                        pdf_url=result.pdf_url,
                        primary_category=result.primary_category,
                        doi=result.doi,
                        journal_ref=result.journal_ref,
                    )
                )
        except arxiv.UnexpectedEmptyPageError as e:
            logger.warning(f"arXiv returned an empty page early: {e}")
        except Exception as e:
            logger.error(f"arXiv fetch failed: {e}")
            raise

        logger.info(f"Fetched {len(papers)} papers from arXiv category={self.category}")
        return papers


if __name__ == "__main__":
    client = ArxivClient()
    for p in client.fetch_recent(max_results=5):
        print(p.arxiv_id, "-", p.title)
