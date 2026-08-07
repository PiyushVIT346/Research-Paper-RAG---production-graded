"""
Feature 7: Airflow DAGs
This DAG lives on an existing Airflow instance (installed via
`pip install apache-airflow` and run standalone -- `airflow standalone` --
no Docker required). Copy this file into Airflow's `dags/` folder.

It calls our own FastAPI service's REST endpoints rather than importing
pipeline code directly, so Airflow's worker environment stays lightweight
and the RAG service can be scaled/deployed independently.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.http.operators.http import SimpleHttpOperator

default_args = {
    "owner": "arxiv-rag",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="arxiv_ingestion_dag",
    description="Fetch new cs.AI papers, parse, chunk, embed, and index -- daily.",
    default_args=default_args,
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["arxiv", "rag", "neon", "opensearch"],
) as dag:

    run_ingestion = SimpleHttpOperator(
        task_id="run_ingestion_pipeline",
        http_conn_id="rag_api",  # Airflow connection pointing at the FastAPI base URL
        endpoint="/ingestion/run",
        method="POST",
        headers={"Content-Type": "application/json"},
        data='{"max_results": 50, "run_in_background": false}',
        response_check=lambda response: response.status_code == 200,
    )

    sync_opensearch = SimpleHttpOperator(
        task_id="sync_to_opensearch",
        http_conn_id="rag_api",
        endpoint="/ingestion/sync-opensearch?limit=200",
        method="POST",
        response_check=lambda response: response.status_code == 200,
    )

    run_ingestion >> sync_opensearch
