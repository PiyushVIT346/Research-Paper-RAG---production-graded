"""Feature 8: OpenSearch Integration -- shared client singleton."""
from opensearchpy import OpenSearch

from config.settings import settings
from src.utils.logging_config import logger

_client: OpenSearch = None


def get_opensearch_client() -> OpenSearch:
    global _client
    if _client is None:
        auth = (settings.opensearch_user, settings.opensearch_password) if settings.opensearch_user else None
        _client = OpenSearch(
            hosts=[settings.opensearch_host],
            http_auth=auth,
            use_ssl=settings.opensearch_host.startswith("https"),
            verify_certs=settings.opensearch_verify_certs,
            ssl_show_warn=False,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )
        info = _client.info()
        logger.info(f"Connected to OpenSearch cluster '{info.get('cluster_name')}' v{info['version']['number']}")
    return _client
