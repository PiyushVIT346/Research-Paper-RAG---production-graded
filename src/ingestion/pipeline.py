"""
Feature 5: Complete Pipeline
End-to-end orchestration: arXiv -> PDF -> Docling -> chunk -> Postgres -> OpenSearch.
Each stage updates `ingestion_status` so the pipeline is resumable -- a
crash mid-run just needs a re-run filtered by status, nothing is lost.
"""
import time
from typing import List

from src.chunking.section_chunker import SectionChunker
from src.db.repository import PaperRepository
from src.ingestion.arxiv_client import ArxivClient
from src.ingestion.docling_parser import DoclingParser
from src.ingestion.pdf_downloader import PDFDownloader
from src.search.sync_pipeline import sync_paper_to_opensearch
from src.utils.logging_config import logger
from src.utils.metrics import PIPELINE_PAPERS_PROCESSED, PIPELINE_ERRORS, timed_stage


class IngestionPipeline:
    def __init__(self):
        self.arxiv_client = ArxivClient()
        self.downloader = PDFDownloader()
        self.parser = DoclingParser()
        self.chunker = SectionChunker()

    def run(self, max_results: int = 5) -> dict:
        start = time.perf_counter()
        stats = {"fetched": 0, "processed": 0, "failed": []}

        with timed_stage("full_pipeline"):
            papers = self.arxiv_client.fetch_recent(max_results=max_results)
            stats["fetched"] = len(papers)

            for paper in papers:
                try:
                    self._process_one(paper.arxiv_id, paper)
                    stats["processed"] += 1
                    PIPELINE_PAPERS_PROCESSED.inc()
                except Exception as e:
                    logger.error(f"Pipeline failed for {paper.arxiv_id}: {e}")
                    PaperRepository.mark_status(paper.arxiv_id, "failed")
                    stats["failed"].append(paper.arxiv_id)

        stats["duration_seconds"] = round(time.perf_counter() - start, 2)
        logger.info(f"Pipeline run complete: {stats}")
        return stats

    def _process_one(self, arxiv_id: str, arxiv_paper) -> None:
        # 1. Persist raw metadata
        PaperRepository.upsert_from_arxiv(arxiv_paper)

        # 2. Download PDF (cached)
        try:
            pdf_path = self.downloader.download(arxiv_id, arxiv_paper.pdf_url)
        except Exception as e:
            PIPELINE_ERRORS.labels(stage="download").inc()
            raise
        PaperRepository.mark_status(arxiv_id, "pdf_downloaded")

        # 3. Parse structure via Docling
        parsed = self.parser.parse(arxiv_id, pdf_path)
        PaperRepository.save_parsed_content(parsed)

        # 4. Section-based chunking with overlap
        chunks = self.chunker.chunk_to_dicts(parsed)
        PaperRepository.save_chunks(arxiv_id, chunks)

        # 5. Embed + index into OpenSearch
        sync_paper_to_opensearch(arxiv_id)


if __name__ == "__main__":
    pipeline = IngestionPipeline()
    print(pipeline.run(max_results=5))
