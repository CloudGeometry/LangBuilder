"""Google Sheets Components for LangBuilder.

This package provides components for authenticating with and interacting with
Google Sheets via the Google Sheets API. Components include:

- GoogleSheetsAuth: Authenticate using service account credentials
- GoogleSheetsRead: Read data from a Google Sheet
- GoogleSheetsWrite: Write data to a Google Sheet
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from langchain_core._api.deprecation import LangChainDeprecationWarning

from langbuilder.components._importing import import_mod

if TYPE_CHECKING:
    from .google_sheets_auth import GoogleSheetsAuth
    from .google_sheets_read import GoogleSheetsRead
    from .google_sheets_write import GoogleSheetsWrite

_dynamic_imports = {
    "GoogleSheetsAuth": "google_sheets_auth",
    "GoogleSheetsRead": "google_sheets_read",
    "GoogleSheetsWrite": "google_sheets_write",
}

__all__ = [
    "GoogleSheetsAuth",
    "GoogleSheetsRead",
    "GoogleSheetsWrite",
]


def __getattr__(attr_name: str) -> Any:
    """Lazily import Google Sheets components on attribute access.

    This enables efficient loading of components only when they are actually used,
    reducing import time and memory overhead.

    Args:
        attr_name: The name of the attribute being accessed.

    Returns:
        The imported component class.

    Raises:
        AttributeError: If the attribute name is not a valid component.
    """
    if attr_name not in _dynamic_imports:
        msg = f"module '{__name__}' has no attribute '{attr_name}'"
        raise AttributeError(msg)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", LangChainDeprecationWarning)
            result = import_mod(attr_name, _dynamic_imports[attr_name], __spec__.parent)
    except (ModuleNotFoundError, ImportError, AttributeError) as e:
        msg = f"Could not import '{attr_name}' from '{__name__}': {e}"
        raise AttributeError(msg) from e
    globals()[attr_name] = result
    return result


def __dir__() -> list[str]:
    """Return the list of available components."""
    return list(__all__)
