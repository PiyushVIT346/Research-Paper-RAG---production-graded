"""Feature 22: RAG query endpoint -- the main product surface."""
from fastapi import APIRouter
from pydantic import BaseModel

from src.rag.agent import run_rag_query

router = APIRouter(prefix="/rag", tags=["rag"])


class RagQueryRequest(BaseModel):
    query: str
    mode: str = "hybrid"   # bm25 | vector | hybrid
    top_k: int = 5


@router.post("/query")
def rag_query(req: RagQueryRequest):
    response = run_rag_query(req.query, mode=req.mode, top_k=req.top_k)
    return response.__dict__
