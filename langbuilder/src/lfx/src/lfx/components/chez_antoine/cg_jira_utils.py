"""Shared utilities for CG-Jira LangBuilder components.

Centralizes auth extraction, ADF conversion, HTTP retry logic,
and response simplification used by all CG-Jira components.
"""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING, Any, Callable

from langflow.schema.data import Data

if TYPE_CHECKING:
    import requests


# ---------------------------------------------------------------------------
# Auth extraction
# ---------------------------------------------------------------------------

def extract_auth(credentials: Any) -> dict:
    """Extract auth headers and base URL from CG-JiraAuth credentials.

    Args:
        credentials: DataInput value from auth_credentials. May be a Data
            object, a dict, or None.

    Returns:
        dict with keys: ``headers`` (dict), ``base_url`` (str).

    Raises:
        ValueError: If credentials are missing, invalid, or report an error.
    """
    auth_data = credentials
    if hasattr(auth_data, "data"):
        auth_data = auth_data.data

    if not isinstance(auth_data, dict):
        raise ValueError(
            "Invalid authentication data. Connect a CG-JiraAuth component."
        )

    if auth_data.get("error"):
        raise ValueError(f"Auth failed: {auth_data['error']}")

    if not auth_data.get("authenticated"):
        raise ValueError(
            "Authentication not established. Check CG-JiraAuth configuration."
        )

    return {
        "headers": auth_data["headers"],
        "base_url": auth_data["jira_url"],
    }


# ---------------------------------------------------------------------------
# ADF conversion
# ---------------------------------------------------------------------------

def text_to_adf(plain_text: str) -> dict:
    """Convert plain text to Atlassian Document Format (ADF).

    Double newlines become paragraph breaks. Single newlines become hard
    breaks within a paragraph.

    Args:
        plain_text: Plain text string.

    Returns:
        Valid ADF document dict.
    """
    if not plain_text or not plain_text.strip():
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": " "}],
                }
            ],
        }

    paragraphs = plain_text.split("\n\n")
    content: list[dict] = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        lines = para.split("\n")
        para_content: list[dict] = []

        for i, line in enumerate(lines):
            if line.strip():
                para_content.append({"type": "text", "text": line.strip()})
            if i < len(lines) - 1:
                para_content.append({"type": "hardBreak"})

        if para_content:
            content.append({"type": "paragraph", "content": para_content})

    if not content:
        content.append(
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": plain_text[:100] or " "}],
            }
        )

    return {"type": "doc", "version": 1, "content": content}


def adf_to_text(adf: dict | None) -> str:
    """Convert ADF document to plain text.

    Walks the ADF node tree and concatenates text nodes, inserting
    newlines for paragraph and hard-break boundaries.

    Args:
        adf: ADF document dict, or ``None``.

    Returns:
        Plain text string.
    """
    if not adf or not isinstance(adf, dict):
        return ""

    parts: list[str] = []

    def _walk(node: dict | list) -> None:
        if isinstance(node, list):
            for item in node:
                _walk(item)
            return

        if not isinstance(node, dict):
            return

        node_type = node.get("type", "")

        if node_type == "text":
            parts.append(node.get("text", ""))
        elif node_type == "hardBreak":
            parts.append("\n")
        elif node_type == "paragraph":
            if parts and not parts[-1].endswith("\n"):
                parts.append("\n\n")
            _walk(node.get("content", []))
        else:
            _walk(node.get("content", []))

    _walk(adf.get("content", []))
    return "".join(parts).strip()


# ---------------------------------------------------------------------------
# Error response builder
# ---------------------------------------------------------------------------

def build_error_response(error: str, error_code: str = "api_error", **defaults: Any) -> Data:
    """Build a structured error Data response.

    Components never raise exceptions to the flow. Instead they return a
    Data object with an ``error`` key.

    Args:
        error: Human-readable error message.
        error_code: Machine-readable error code.
        **defaults: Additional keys to include (e.g. ``issue_key=None``).

    Returns:
        Data object with error information and supplied defaults.
    """
    data = {**defaults, "error": error, "error_code": error_code}
    return Data(data=data)


# ---------------------------------------------------------------------------
# HTTP request with retry
# ---------------------------------------------------------------------------

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1.0
MAX_DELAY = 60.0
REQUEST_TIMEOUT = 30


def jira_request(
    method: str,
    url: str,
    headers: dict,
    *,
    log: Callable[..., Any] | None = None,
    timeout: int = REQUEST_TIMEOUT,
    **kwargs: Any,
) -> "requests.Response":
    """Make an HTTP request to Jira with exponential backoff on 429.

    Args:
        method: HTTP method (``"GET"``, ``"POST"``, ``"PUT"``, ``"DELETE"``).
        url: Full request URL.
        headers: Auth headers dict.
        log: Optional logging callback (``self.log``).
        timeout: Request timeout in seconds.
        **kwargs: Passed through to ``requests.request()`` (e.g. ``json=``,
            ``params=``).

    Returns:
        The ``requests.Response`` object.

    Raises:
        requests.exceptions.Timeout: On request timeout (not retried).
        requests.exceptions.ConnectionError: On connection failure (not retried).
        RuntimeError: If all retries are exhausted on 429.
    """
    import requests as _requests

    _log = log or (lambda *a, **kw: None)

    for attempt in range(MAX_RETRIES):
        response = _requests.request(
            method,
            url,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )

        if response.status_code != 429:
            return response

        # Rate limited — exponential backoff
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                wait = int(retry_after)
            except ValueError:
                wait = _backoff_delay(attempt)
        else:
            wait = _backoff_delay(attempt)

        _log(
            f"Rate limited (429). Retry {attempt + 1}/{MAX_RETRIES} "
            f"in {wait:.1f}s"
        )
        time.sleep(wait)

    raise RuntimeError(
        f"Jira rate limit exceeded after {MAX_RETRIES} retries for {method} {url}"
    )


def _backoff_delay(attempt: int) -> float:
    """Exponential backoff with jitter: 1s, 3s, 9s."""
    delay = min(BASE_DELAY * (3 ** attempt), MAX_DELAY)
    jitter = random.uniform(0, delay * 0.1)
    return delay + jitter


# ---------------------------------------------------------------------------
# Response simplification
# ---------------------------------------------------------------------------

def simplify_issue(issue: dict) -> dict:
    """Extract key fields from a raw Jira issue response.

    Args:
        issue: Raw issue dict from the Jira API.

    Returns:
        Simplified dict with commonly used fields.
    """
    fields = issue.get("fields", {})

    status_obj = fields.get("status") or {}
    priority_obj = fields.get("priority") or {}
    assignee_obj = fields.get("assignee") or {}
    reporter_obj = fields.get("reporter") or {}
    issuetype_obj = fields.get("issuetype") or {}

    return {
        "key": issue.get("key"),
        "id": issue.get("id"),
        "summary": fields.get("summary", ""),
        "status": status_obj.get("name", ""),
        "status_category": (status_obj.get("statusCategory") or {}).get("key", ""),
        "priority": priority_obj.get("name", ""),
        "issue_type": issuetype_obj.get("name", ""),
        "assignee": extract_user(assignee_obj) if assignee_obj else None,
        "reporter": extract_user(reporter_obj) if reporter_obj else None,
        "labels": fields.get("labels", []),
        "created": fields.get("created", ""),
        "updated": fields.get("updated", ""),
    }


def extract_user(user: dict) -> dict | None:
    """Simplify a Jira user object.

    Args:
        user: Raw user dict from the Jira API.

    Returns:
        Simplified dict, or ``None`` if input is empty/None.
    """
    if not user:
        return None

    return {
        "account_id": user.get("accountId", ""),
        "display_name": user.get("displayName", ""),
        "email": user.get("emailAddress", ""),
        "active": user.get("active", True),
    }


# ---------------------------------------------------------------------------
# Jira error response parser
# ---------------------------------------------------------------------------

def parse_jira_error(response: "requests.Response") -> str:
    """Extract a human-readable error message from a Jira API error response.

    Args:
        response: The ``requests.Response`` object.

    Returns:
        Error message string.
    """
    try:
        data = response.json()
        if "errorMessages" in data and data["errorMessages"]:
            return "; ".join(data["errorMessages"])
        if "errors" in data and data["errors"]:
            return "; ".join(f"{k}: {v}" for k, v in data["errors"].items())
        if "message" in data:
            return data["message"]
    except Exception:
        pass

    return response.text[:500] if response.text else f"HTTP {response.status_code}"


def error_code_from_status(status_code: int) -> str:
    """Map HTTP status code to a machine-readable error code.

    Args:
        status_code: HTTP response status code.

    Returns:
        Error code string.
    """
    mapping = {
        400: "validation_error",
        401: "auth_failed",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        429: "rate_limited",
    }
    return mapping.get(status_code, "api_error" if status_code >= 500 else "api_error")
