# ArXivIQ — intelligent search & Q&A over research papers

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![RAG](https://img.shields.io/badge/RAG-Retrieval%20Augmented%20Generation-purple)](#)
[![OpenSearch](https://img.shields.io/badge/OpenSearch-Search%20Engine-005EB8?logo=opensearch&logoColor=white)](https://opensearch.org/)
[![Redis](https://img.shields.io/badge/Redis-Cache-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Langfuse](https://img.shields.io/badge/Langfuse-LLM%20Observability-orange)](https://langfuse.com/)
[![Jina AI](https://img.shields.io/badge/Jina%20AI-Embeddings-000000)](https://jina.ai/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?logo=github&logoColor=white)](https://github.com/PiyushVIT346/Research-Paper-RAG---production-graded)

![GitHub stars](https://img.shields.io/github/stars/PiyushVIT346/Research-Paper-RAG---production-graded?style=flat-square)
![GitHub forks](https://img.shields.io/github/forks/PiyushVIT346/Research-Paper-RAG---production-graded?style=flat-square)
![GitHub issues](https://img.shields.io/github/issues/PiyushVIT346/Research-Paper-RAG---production-graded?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/PiyushVIT346/Research-Paper-RAG---production-graded?style=flat-square)


</div>

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
<table>
  <tr>
    <td><img src="https://github.com/PiyushVIT346/Research-Paper-RAG---production-graded/blob/main/architecture.png" width="1000"></td>
   
  </tr>
</table>

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

## Implementation/ Work
<table>
  <tr>
    <td align="center">
      <img src="https://github.com/PiyushVIT346/Research-Paper-RAG---production-graded/blob/main/Screenshot%202026-08-06%20224857.jpg" width="500">
      <br>
      <b>Neon Dashboard</b>
    </td>
    <td align="center">
      <img src="https://github.com/PiyushVIT346/Research-Paper-RAG---production-graded/blob/main/Screenshot%202026-08-06%20230333.jpg" width="500">
      <br>
      <b>Opensearch Dashboard</b>
    </td>
  </tr>
</table>
<table>
  <tr>
    <td align="center">
      <img src="https://github.com/PiyushVIT346/Research-Paper-RAG---production-graded/blob/main/Screenshot%202026-08-06%20231436.jpg" width="500">
      <br>
      <b>Opensearch Filtering (BM25 keyword search)</b>
    </td>
    <td align="center">
      <img src="https://github.com/PiyushVIT346/Research-Paper-RAG---production-graded/blob/main/Screenshot%202026-08-06%20234917.jpg" width="500">
      <br>
      <b>API Setup</b>
    </td>
  </tr>
</table>
<table>
  <tr>
    <td align="center">
      <img src="https://github.com/PiyushVIT346/Research-Paper-RAG---production-graded/blob/main/Screenshot%202026-08-09%20000100.jpg" width="500">
      <br>
      <b>LangFuse Dashboard</b>
    </td>
    <td align="center">
      <img src="https://github.com/PiyushVIT346/Research-Paper-RAG---production-graded/blob/main/Screenshot%202026-08-06%20224734.jpg" width="500">
      <br>
      <b>Ingestion and chunking via Neon to OpenSearch</b>
    </td>
  </tr>
</table>

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

## Setup 

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

## Opensearch 
OpenSearch is an open-source, distributed search and analytics engine that can work as the retrieval layer of a RAG pipeline. It supports traditional full-text search, vector/semantic search, and hybrid search in the same system.  
OpenSearch can combine keyword search (BM25) and semantic/vector search through its hybrid-search functionality. This is useful because keyword search is good at exact terms, IDs, names, and technical terminology, while semantic search is better at understanding the meaning of a natural-language query.
It also supports neural sparse search, which uses sparse representations with an inverted-index approach, providing a semantic-search alternative that can be more efficient than dense k-NN search in some workloads
It can be more production-oriented than a simple setup

| Feature                | Traditional RAG setup                   | OpenSearch                        |
| ---------------------- | --------------------------------------- | --------------------------------- |
| Keyword search         | BM25 separately                         | Built-in                          |
| Vector search          | FAISS/vector DB                         | Built-in                          |
| Hybrid search          | Often custom fusion                     | Built-in hybrid queries/pipelines |
| Sparse semantic search | Usually additional component            | Built-in neural sparse search     |
| Metadata filtering     | Custom implementation                   | Native filtering                   |
| Scaling                | Requires architecture around components | Distributed search engine         |
| Monitoring/analytics   | Additional tools                        | OpenSearch ecosystem              |
| Search experimentation | Mostly code-based                       | Dashboards + query tools           |
| Production search      | Multiple components                     | Unified search platform            |


OpenSearch acts as the production-grade retrieval and search engine for RAG, combining BM25, vector and neural-sparse retrieval with hybrid ranking, filtering, scalability and observability, while OpenSearch Dashboards provides the UI to inspect, query, analyze and monitor that retrieval system.

---

## Redis for Caching
Redis is an in-memory data store commonly used in RAG systems to cache frequently accessed or expensive-to-compute data. It stores data primarily in RAM, making read/write operations extremely fast.
Redis can cache things such as:

Frequently asked questions and their answers
- Embeddings
- Retrieved document chunks
- LLM responses
- Session/conversation data
- Intermediate RAG results

| Feature             | Traditional Methods                 | Redis                                           |
| ------------------- | ----------------------------------- | ----------------------------------------------- |
| Storage             | Disk / database                     | Primarily in-memory                             |
| Read/write speed    | Relatively slower                   | Extremely fast                                  |
| Data structures     | Usually key-value/files             | Strings, Lists, Sets, Hashes, Sorted Sets, etc. |
| Expiration          | Often manually implemented          | Built-in TTL                                    |
| Concurrent access   | Depends on implementation           | Designed for high concurrency                   |
| Distributed caching | Requires additional infrastructure | Supports distributed deployments                |
| RAG suitability     | Requires custom integration         | Well suited for low-latency caching             |
| Persistence         | Usually persistent by default       | Optional persistence                            |
| Scalability         | Depends on storage system           | Horizontally scalable with Redis Cluster        |

### Redis vs common alternatives

1. Database caching

Using PostgreSQL/MySQL directly for caching is possible, but database queries involve disk/storage and database processing overhead. Redis is optimized specifically for very fast in-memory access.

2. File-based caching

```
Application → File System → Read/Write
```
This is simple but generally unsuitable for high-concurrency production RAG systems because disk I/O is slower and distributed access is more complicated.

3. Python in-memory dictionaries
```
cache = {
    "query": "answer"
}
```
This is extremely simple and fast, but the cache exists only inside one application process. It is lost when the application restarts and is difficult to share across multiple application instances.

### Redis provides a shared caching layer:
```
             ┌───────────────┐
App Server 1 ─┤               │
App Server 2 ─┤    Redis      │
App Server 3 ─┤    Cache      │
             └───────────────┘
```
### Why Redis is useful for RAG

RAG pipelines can involve expensive operations such as embedding generation, vector retrieval, reranking, and LLM inference. If the same or similar request occurs repeatedly, Redis can return a previously computed result instead of executing the entire pipeline again.

---
## Jina AI for Embeddings
Jina AI provides embedding models designed to convert text, documents, queries, and other data into dense vector representations. In a RAG system, these embeddings allow semantically similar content to be retrieved even when the query and document use different words.
### Traditional Embedding Methods
|  Method	                        |  Approach	                          |  Limitation                                  |
| --------------------------------- | ----------------------------------- | -------------------------------------------- |
|TF-IDF	                           |  Word-frequency based	              | Doesn't understand semantic meaning          |
|Bag of Words	                     |  Word occurrence/count	           | Ignores word relationships and context       |
|Word2Vec	                        |  Word-level embeddings	           | Limited contextual understanding             |
|GloVe	                           |  Global word co-occurrence	        | Mainly word-level representation             |
|Traditional sentence embeddings	   |  Fixed pretrained representations	  | Often weaker for modern retrieval tasks      |
|Open-source transformer embeddings |	Transformer-based	                 | Quality varies significantly between models  |

---

## Langfuse
Langfuse is an open-source LLM observability and tracing platform used to monitor, debug, and evaluate LLM and RAG applications. It provides visibility into the complete flow of a request—from the user query and retrieval step to prompt execution and final LLM response.
It can track information such as:

- LLM traces — Follow the complete execution flow.
- Latency — Identify slow retrieval, reranking, or LLM operations.
- Token usage & costs — Monitor LLM consumption.
- Prompts & responses — Inspect inputs and generated outputs.
- Evaluation — Measure and compare RAG/LLM performance.
- Debugging — Identify where incorrect or low-quality responses originate.


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

