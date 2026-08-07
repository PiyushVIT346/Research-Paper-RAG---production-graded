"""
Feature 7: Trigger the Airflow DAG run via Airflow's REST API
(https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html)
instead of the CLI -- lets our FastAPI service or any external caller kick
off ingestion on demand without SSH/CLI access to the Airflow host.
"""
import sys
from datetime import datetime, timezone

import requests
from requests.auth import HTTPBasicAuth

from config.settings import settings


def trigger_dag_run() -> dict:
    url = f"{settings.airflow_base_url}/api/v1/dags/{settings.airflow_dag_id}/dagRuns"
    payload = {
        "dag_run_id": f"manual__{datetime.now(timezone.utc).isoformat()}",
        "logical_date": datetime.now(timezone.utc).isoformat(),
    }
    resp = requests.post(
        url,
        json=payload,
        auth=HTTPBasicAuth(settings.airflow_username, settings.airflow_password),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    result = trigger_dag_run()
    print(result)
    sys.exit(0)
