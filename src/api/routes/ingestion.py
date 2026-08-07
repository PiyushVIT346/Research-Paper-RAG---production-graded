"""Feature 5/7: trigger ingestion pipeline manually or via Airflow REST callback."""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from src.ingestion.pipeline import IngestionPipeline
from src.search.sync_pipeline import sync_all_pending

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class IngestRequest(BaseModel):
    max_results: int = 20
    run_in_background: bool = True


@router.post("/run")
def run_ingestion(req: IngestRequest, background_tasks: BackgroundTasks):
    pipeline = IngestionPipeline()
    if req.run_in_background:
        background_tasks.add_task(pipeline.run, req.max_results)
        return {"status": "started", "max_results": req.max_results}
    return pipeline.run(max_results=req.max_results)


@router.post("/sync-opensearch")
def run_sync(limit: int = 100):
    """Manually trigger the Postgres -> OpenSearch sync (normally Airflow does this)."""
    return sync_all_pending(limit=limit)
