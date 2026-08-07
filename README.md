# ArXivIQ — intelligent search & Q&A over research papers

A production-grade Retrieval-Augmented Generation system over arXiv cs.AI
research papers. Pure Python processes (no Docker anywhere) — everything
runs as plain local/managed services talking over HTTP(S): Neon Postgres,
OpenSearch, Redis, Gemini, Jina AI, and LangFuse.

Built end-to-end: rate-limited ingestion → structured parsing → chunking →
embedding → hybrid search → an agentic RAG loop with guardrails, query
refinement, document grading, retries, caching, and full tracing.

---

## What it does

1. Pulls the latest `cs.AI` papers from arXiv (rate-limited, cached PDFs)
2. Parses each PDF and chunks it with overlap for retrieval
3. Stores structured paper data in Postgres (Neon) and embeddings + chunks in OpenSearch
4. Answers natural-language research questions through an **agentic RAG pipeline**:
   - **Guardrail** — an LLM scores query relevance 0–100; out-of-scope queries (e.g. "What is a dog?") are rejected before any retrieval happens
   - **Query refinement** — vague queries get rewritten for better retrieval
   - **Hybrid retrieval** — BM25 + kNN vector search fused client-side
   - **Document grading** — an LLM filters out irrelevant retrieved chunks
   - **Iterative retry** — refines and retries (max 2 attempts) if too few relevant chunks are found
   - **Answer generation** — Gemini generates a grounded, cited answer
   - **Reasoning transparency** — every stage's reasoning is returned to the caller
5. Caches full responses in Redis for sub-second repeat queries, and traces every stage in LangFuse

---

## Architecture

```
┌─────────────┐   ┌──────────────┐   ┌───────────────┐   ┌──────────────┐
│ arXiv API   │──▶│ PDF Download │──▶│ PDF Parser    │──▶│ Section      │
│ (rate-      │   │ + local cache│   │ (pypdf; text  │   │ Chunker      │
│  limited)   │   │              │   │  extraction)  │   │ (overlap)    │
└─────────────┘   └──────────────┘   └───────────────┘   └──────┬───────┘
                                                                  │
      ┌──────────────────────────────  Neon PostgreSQL  ◀────────┘
      │        (papers, sections, chunks -- source of truth)
      ▼
┌─────────────┐   ┌───────────────┐
│ Jina        │──▶│ OpenSearch    │◀── Airflow DAG (optional, via REST API)
│ Embeddings  │   │ arxiv-papers  │
└─────────────┘   │ index (BM25 + │
                   │ kNN vector)   │
                   └───────┬───────┘
                           │
                           ▼
        ┌───────────────────────────────────────┐
        │        FastAPI  (RAG Agent)           │
        │  Guardrail(0-100) → Refine → Retrieve │
        │  (hybrid search) → Grade → [retry≤2]  │
        │  → Gemini generate → Redis cache      │
        │        (LangFuse traces every step)   │
        └───────────────────────────────────────┘
```

---

## Feature → file map

| # | Feature | File(s) |
|---|---|---|
| 1 | arXiv API client, rate limiting | `src/ingestion/arxiv_client.py` |
| 2 | PDF download + local cache | `src/ingestion/pdf_downloader.py` |
| 3 | PDF parsing (structured text) | `src/ingestion/docling_parser.py`, `src/ingestion/models.py` |
| 4 | Postgres (Neon) integration | `src/db/models.py`, `connection.py`, `repository.py` |
| 5 | Complete ingestion pipeline | `src/ingestion/pipeline.py` |
| 6 | Production readiness | `src/utils/logging_config.py`, `src/utils/metrics.py` |
| 7 | Airflow DAG via REST | `airflow_dags/arxiv_ingestion_dag.py`, `scripts/trigger_airflow_dag.py` |
| 8 | OpenSearch integration | `src/search/opensearch_client.py` |
| 9 | Index management/mappings | `src/search/index_manager.py` |
| 10 | BM25 search | `src/search/bm25_search.py` |
| 11 | Postgres → OpenSearch sync + query types | `src/search/sync_pipeline.py`, `src/search/hybrid_search.py` |
| 12 | Section-based chunking | `src/chunking/section_chunker.py` |
| 13 | Jina embeddings | `src/embeddings/jina_embedder.py` |
| 14 | Unified search (BM25/vector/hybrid) | `src/search/hybrid_search.py` |
| 15 | Performance analysis | `/metrics` endpoint, per-stage timing histograms |
| 16 | Gemini LLM integration | `src/rag/llm_gemini.py` |
| 17 | Prompt-optimized generation | cached system instruction, trimmed context, capped tokens (see docstring in `llm_gemini.py`) |
| 18 | Redis response caching | `src/rag/cache.py` |
| 19 | LangFuse observability | `src/rag/tracing.py` |
| 20 | Sub-second cached responses | cache-first check in `src/rag/agent.py` |
| 21 | Production monitoring | `src/api/routes/health.py` (`/metrics`), structured logs |
| — | Guardrail / refine / grade / retry / reasoning | `src/rag/guardrail.py`, `query_refiner.py`, `document_grader.py`, `agent.py` |
| 22 | Search + RAG REST API | `src/api/routes/search.py`, `src/api/routes/rag.py` |

---

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Metadata store | PostgreSQL (Neon, serverless) |
| Search / vector store | OpenSearch (BM25 + kNN) |
| Embeddings | Jina AI (`jina-embeddings-v3`) |
| LLM | Google Gemini |
| Cache | Redis |
| Observability | LangFuse, Prometheus metrics |
| Orchestration | Apache Airflow (triggered via REST, not embedded) |
| PDF parsing | pypdf |

---

## Setup (no Docker)

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# fill in: NEON_DATABASE_URL, OPENSEARCH_HOST/creds, JINA_API_KEY,
#          GEMINI_API_KEY, REDIS_URL, LANGFUSE keys, AIRFLOW_* creds
```

**1. Create the Postgres schema on Neon**
```bash
python -m src.db.connection
```

**2. Start OpenSearch** (local install or managed — see notes below), then create the index:
```bash
python -m src.search.index_manager
```

**3. Start Redis** (local service or managed, e.g. Upstash)

**4. Run ingestion**
```bash
python -m src.ingestion.pipeline
```

**5. Start the API**
```bash
uvicorn src.api.main:app --reload --port 8000
```
Visit `http://localhost:8000/docs` for interactive Swagger docs.

**6. (Optional) Airflow** for scheduled ingestion — run `apache-airflow` standalone, add an HTTP connection `rag_api` pointing at the FastAPI base URL, and drop `airflow_dags/arxiv_ingestion_dag.py` into Airflow's `dags/` folder.

---

## Using the API

```bash
# Trigger ingestion (arXiv -> Postgres -> OpenSearch)
curl -X POST localhost:8000/ingestion/run \
     -H "Content-Type: application/json" \
     -d '{"max_results": 20, "run_in_background": false}'

# Search
curl "localhost:8000/search/bm25?q=transformer+attention"
curl "localhost:8000/search/vector?q=chain+of+thought+reasoning"
curl "localhost:8000/search/hybrid?q=reinforcement+learning+from+human+feedback"

# Full agentic RAG query
curl -X POST localhost:8000/rag/query \
     -H "Content-Type: application/json" \
     -d '{"query": "What are the main approaches to reducing hallucination in LLMs?"}'

# Out-of-scope query -> rejected by the guardrail before any retrieval
curl -X POST localhost:8000/rag/query \
     -H "Content-Type: application/json" \
     -d '{"query": "What is a dog?"}'
```

---

## Windows-specific notes (learned the hard way)

If you're running this on Windows, a few real-world gotchas surfaced during setup that are worth knowing up front:

- **PDF parsing uses `pypdf`, not Docling.** Docling's layout model depends on native PyTorch compilation (`cl.exe`/MSVC) and heavy RAM, which caused repeated access violations and `std::bad_alloc` crashes on Windows. `docling_parser.py` was swapped for a lightweight `pypdf`-based extractor with the same `ParsedPaper` interface — you lose true structured table/figure detection but gain a setup that reliably runs anywhere. Extracted text is sanitized of NUL bytes (`\x00`), which Postgres rejects and which `pypdf` occasionally emits.
- **OpenSearch k-NN engine must be `lucene`, not `nmslib`.** OpenSearch 3.0+ deprecated `nmslib` for new indices; the mapping in `index_manager.py` uses the built-in `lucene` HNSW engine instead, which needs no extra native library.
- **`SessionLocal` uses `expire_on_commit=False`.** Without this, SQLAlchemy objects returned from a closed session raise `Instance is not bound to a Session` errors when accessed later in the pipeline.
- **Redis on Windows**: the official Redis project doesn't ship Windows builds. Use `winget install Redis.Redis` or the [Memurai](https://www.memurai.com/get-memurai) Redis-compatible server, both of which install as a Windows Service (`Get-Service Redis`).
- **OpenSearch/Dashboards run as plain unpacked zips**, started with `opensearch.bat` / `opensearch-dashboards.bat` — no Docker needed. If the security plugin is disabled (common for local dev), use `http://` not `https://` and leave `OPENSEARCH_USER`/`PASSWORD` blank.
- **LangFuse SDK v4** uses `start_span()` (OpenTelemetry-based), not the older `.trace()` API from SDK v2. `tracing.py` wraps every call in try/except so tracing issues never break the actual RAG request — observability is never on the critical path.
- **PowerShell JSON quoting**: use single quotes around JSON bodies with `curl.exe -d '{"query": "..."}'`, or use `Invoke-RestMethod -Body '...'`, to avoid PowerShell mangling escaped double quotes.

---

## Getting OpenSearch credentials

**Local (dev, fastest):** download the OpenSearch zip, set `OPENSEARCH_INITIAL_ADMIN_PASSWORD`, run `opensearch.bat`/`opensearch-tar-install.sh`. See setup notes above.

**Managed (for a persistent deployment):**
- **AWS OpenSearch Service** — create a domain, enable fine-grained access control with a master username/password, use the domain endpoint as `OPENSEARCH_HOST`.
- **Aiven for OpenSearch** — sign up, create a service, split the given Service URI into host/user/password.

`OPENSEARCH_INDEX` stays `arxiv-papers` either way — that's the index name our code creates, not something the provider gives you.

---

## Verified during build

- All modules byte-compile cleanly and the chunking logic (`tests/test_chunking.py`) passes unit tests with no external services required.
- The arXiv rate limiter enforces its configured minimum interval between calls.
- Full pipeline run confirmed end-to-end on Windows: arXiv fetch → PDF download → parse → chunk → Jina embed → OpenSearch index, with all 5 test papers reaching `ingestion_status = 'indexed'`.
- RAG query endpoint confirmed reachable through the full guardrail → retrieve → grade → generate chain.

---

## Notes / production hardening ideas

- Add Alembic migrations instead of `create_all` for schema evolution (currently, schema changes on an existing table require manual `drop_all`/`create_all`).
- Add API-key auth middleware to FastAPI before exposing publicly.
- Hybrid search fusion is client-side min-max normalization; if your OpenSearch has the Neural Search plugin, swap in its native `hybrid` query pipeline for server-side fusion.
- Guardrail/refine/grade all call Gemini — consider a distilled classifier for the guardrail step alone to cut latency at scale.
- Isolate all Python dependencies in a proper `venv` per-project (global installs can silently drift package versions, as happened with the LangFuse SDK during development).
