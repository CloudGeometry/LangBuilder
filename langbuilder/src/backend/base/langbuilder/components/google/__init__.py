from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langbuilder.components._importing import import_mod

if TYPE_CHECKING:
    from langbuilder.components.google.gmail import GmailLoaderComponent
    from langbuilder.components.google.google_bq_sql_executor import BigQueryExecutorComponent
    from langbuilder.components.google.google_drive import GoogleDriveComponent
    from langbuilder.components.google.google_drive_docs_parser import GoogleDriveDocsParserSA
    from langbuilder.components.google.google_drive_docs_watcher import GoogleDriveDocsWatcher
    from langbuilder.components.google.google_drive_search import GoogleDriveSearchComponent
    from langbuilder.components.google.google_generative_ai import GoogleGenerativeAIComponent
    from langbuilder.components.google.google_generative_ai_embeddings import GoogleGenerativeAIEmbeddingsComponent
    from langbuilder.components.google.google_oauth_token import GoogleOAuthToken

_dynamic_imports = {
    "GmailLoaderComponent": "gmail",
    "BigQueryExecutorComponent": "google_bq_sql_executor",
    "GoogleDriveComponent": "google_drive",
    "GoogleDriveDocsParserSA": "google_drive_docs_parser",
    "GoogleDriveDocsWatcher": "google_drive_docs_watcher",
    "GoogleDriveSearchComponent": "google_drive_search",
    "GoogleGenerativeAIComponent": "google_generative_ai",
    "GoogleGenerativeAIEmbeddingsComponent": "google_generative_ai_embeddings",
    "GoogleOAuthToken": "google_oauth_token",
}

__all__ = [
    "GmailLoaderComponent",
    "BigQueryExecutorComponent",
    "GoogleDriveComponent",
    "GoogleDriveDocsParserSA",
    "GoogleDriveDocsWatcher",
    "GoogleDriveSearchComponent",
    "GoogleGenerativeAIComponent",
    "GoogleGenerativeAIEmbeddingsComponent",
    "GoogleOAuthToken",
]


def __getattr__(attr_name: str) -> Any:
    """Lazily import Google components on attribute access."""
    if attr_name not in _dynamic_imports:
        msg = f"module '{__name__}' has no attribute '{attr_name}'"
        raise AttributeError(msg)
    try:
        result = import_mod(attr_name, _dynamic_imports[attr_name], __spec__.parent)
    except (ModuleNotFoundError, ImportError, AttributeError) as e:
        msg = f"Could not import '{attr_name}' from '{__name__}': {e}"
        raise AttributeError(msg) from e
    globals()[attr_name] = result
    return result


def __dir__() -> list[str]:
    return list(__all__)
