"""
Slack Base Mixin

Shared foundation for Slack components: generic API caller, token resolution,
rate-limit retry, structured error responses, and standardized logging.

Designed as a mixin (no LangBuilder base class inheritance) to avoid MRO
conflicts when mixed into LCToolComponent subclasses.

Adapted for LangBuilder 1.65+ (CloudGeometry fork)
"""

from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SLACK_API_BASE = "https://slack.com/api"
MAX_MESSAGE_LENGTH = 4000
REQUEST_TIMEOUT = 10
MAX_RATE_LIMIT_WAIT = 60
DEFAULT_RATE_LIMIT_WAIT = 30

# ---------------------------------------------------------------------------
# Human-readable error messages keyed by Slack error codes and internal codes
# ---------------------------------------------------------------------------
SLACK_ERROR_MESSAGES: dict[str, str] = {
    # Auth errors
    "invalid_auth": "Authentication failed. The token is invalid or expired.",
    "token_revoked": "The token has been revoked. Reinstall the Slack app.",
    "not_authed": "No authentication token provided.",
    "missing_scope": (
        "The token is missing a required OAuth scope. "
        "Check the required scopes in the component documentation."
    ),
    "account_inactive": "The token owner's account has been deactivated.",
    "org_login_required": "Organization login is required for this workspace.",
    # Channel errors
    "channel_not_found": (
        "Channel not found. Verify the channel ID exists and the bot has access."
    ),
    "not_in_channel": (
        "The bot is not a member of this channel. "
        "Invite the bot or use a public channel with chat:write.public scope."
    ),
    "is_archived": "Cannot operate on an archived channel.",
    "channel_is_archived": "Cannot operate on an archived channel.",
    # User errors
    "user_not_found": "User not found for the provided identifier.",
    "users_not_found": "User not found for the provided email address.",
    # Message errors
    "message_not_found": "The specified message was not found.",
    "cant_update_message": "Cannot update this message (not the author or insufficient permissions).",
    "cant_delete_message": "Cannot delete this message (not the author or insufficient permissions).",
    "no_text": "Message content is required (text or blocks).",
    "too_many_attachments": "Too many attachments on this message.",
    # Reaction errors
    "already_reacted": "This reaction has already been added to the message.",
    "no_item_specified": "No message specified for the reaction.",
    "invalid_name": "Invalid emoji name.",
    # File errors
    "file_not_found": "The specified file was not found.",
    "file_too_large": "The file exceeds the workspace size limit.",
    # Rate limiting
    "rate_limited": "Rate limit exceeded after retry. Try again later.",
    "ratelimited": "Rate limit exceeded after retry. Try again later.",
    # Network / internal errors
    "timeout": "Request timed out. Slack may be experiencing issues.",
    "connection_error": "Could not connect to Slack API. Check network connectivity.",
    "request_error": "HTTP request to Slack API failed.",
    "json_parse_error": "Failed to parse Slack API response as JSON.",
    "invalid_input": "Invalid input. Check required fields for the selected operation.",
    # Modal / views errors
    "expired_trigger_id": (
        "The trigger_id has expired (3-second limit). "
        "The modal must be opened immediately after receiving the Slack event."
    ),
    "invalid_trigger_id": "The trigger_id is invalid or has already been used.",
    "view_too_large": "The modal view JSON exceeds Slack's size limit.",
    "duplicate_external_id": "A view with this external_id is already open.",
    "view_not_found": "The specified view was not found (invalid view_id).",
    "hash_conflict": (
        "The view was modified by another request. "
        "Re-fetch the view and retry with the updated hash."
    ),
}


class SlackBaseMixin:
    """Shared infrastructure for Slack components.

    Provides:
    - ``_slack_api()``  -- generic Slack Web API caller with rate-limit retry
    - ``_get_slack_token()`` -- token resolution (input > env var)
    - ``_slack_log()`` -- structured logging helper

    This is a **mixin**, not a base class. It does not inherit from
    ``Component`` or ``LCToolComponent`` to avoid diamond inheritance.
    """

    # ------------------------------------------------------------------
    # Token resolution
    # ------------------------------------------------------------------
    def _get_slack_token(self) -> str:
        """Resolve the Slack bot token.

        Priority:
            1. ``self.slack_bot_token`` component input
            2. ``SLACK_BOT_TOKEN`` environment variable

        Returns:
            The resolved token string.

        Raises:
            ValueError: If no token is available.
        """
        token = getattr(self, "slack_bot_token", None)
        if token:
            return str(token)

        env_token = os.environ.get("SLACK_BOT_TOKEN")
        if env_token:
            return env_token

        msg = (
            "No Slack bot token provided. "
            "Set the 'Slack Bot Token' input or the SLACK_BOT_TOKEN environment variable."
        )
        raise ValueError(msg)

    # ------------------------------------------------------------------
    # Generic Slack API caller
    # ------------------------------------------------------------------
    def _slack_api(
        self,
        method: str,
        endpoint: str,
        token: str,
        *,
        timeout: int = REQUEST_TIMEOUT,
        max_retries: int = 1,
        **kwargs,
    ) -> dict:
        """Call a Slack Web API endpoint with structured error handling.

        Args:
            method: HTTP method (``"GET"`` or ``"POST"``).
            endpoint: Slack API endpoint name, e.g. ``"chat.postMessage"``.
            token: Bearer token for the ``Authorization`` header.
            timeout: Request timeout in seconds.
            max_retries: Number of retries on HTTP 429 rate-limit responses.
            **kwargs: Passed directly to ``requests.request``.  Use ``json=``
                for JSON POST bodies, ``data=`` for form-encoded POST bodies,
                or ``params=`` for GET query parameters.

        Returns:
            A dict with the shape::

                {
                    "ok": bool,
                    "data": dict | None,   # full Slack JSON on success
                    "error": str | None,    # human-readable message on failure
                    "error_code": str | None,
                    "http_status": int | None,
                }
        """
        import requests as req_lib

        url = f"{SLACK_API_BASE}/{endpoint}"
        headers = {"Authorization": f"Bearer {token}"}

        # Content-Type handling
        if "json" in kwargs:
            headers["Content-Type"] = "application/json"
        elif "data" in kwargs and method.upper() == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        # Merge caller-provided headers (if any) with ours
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        for attempt in range(max_retries + 1):
            try:
                response = req_lib.request(
                    method.upper(),
                    url,
                    headers=headers,
                    timeout=timeout,
                    **kwargs,
                )
            except req_lib.exceptions.Timeout:
                return self._api_error("timeout", timeout=timeout)
            except req_lib.exceptions.ConnectionError:
                return self._api_error("connection_error")
            except req_lib.exceptions.RequestException as exc:
                return self._api_error(
                    "request_error",
                    detail=str(exc),
                    http_status=None,
                )

            # ---- Rate-limit handling (HTTP 429) ----
            if response.status_code == 429:
                if attempt < max_retries:
                    retry_after = self._parse_retry_after(response)
                    self._slack_log(
                        "warning",
                        endpoint,
                        f"Rate limited. Retrying in {retry_after}s "
                        f"(attempt {attempt + 2}/{max_retries + 1})",
                    )
                    time.sleep(retry_after)
                    continue
                # Exhausted retries
                return self._api_error("rate_limited", http_status=429)

            # ---- Non-200 HTTP errors (500, 503, etc.) ----
            if response.status_code != 200:
                return self._api_error(
                    "request_error",
                    detail=f"HTTP {response.status_code}",
                    http_status=response.status_code,
                )

            # ---- Parse JSON body ----
            try:
                data = response.json()
            except (ValueError, TypeError):
                return self._api_error("json_parse_error", http_status=200)

            # ---- CRITICAL: Slack returns HTTP 200 even on errors ----
            # The actual success/failure is in the JSON body's "ok" field.
            if data.get("ok"):
                return {
                    "ok": True,
                    "data": data,
                    "error": None,
                    "error_code": None,
                    "http_status": 200,
                }

            error_code = data.get("error", "unknown_error")
            human_msg = SLACK_ERROR_MESSAGES.get(
                error_code, f"Slack API error: {error_code}"
            )
            self._slack_log("error", endpoint, f"{error_code}: {human_msg}")
            return {
                "ok": False,
                "data": data,
                "error": human_msg,
                "error_code": error_code,
                "http_status": 200,
            }

        # Should not reach here, but defensive return
        return self._api_error("rate_limited", http_status=429)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_retry_after(response) -> int:
        """Extract and cap the ``Retry-After`` header value."""
        raw = response.headers.get("Retry-After", DEFAULT_RATE_LIMIT_WAIT)
        try:
            seconds = int(raw)
        except (ValueError, TypeError):
            seconds = DEFAULT_RATE_LIMIT_WAIT
        return min(seconds, MAX_RATE_LIMIT_WAIT)

    def _api_error(
        self,
        code: str,
        *,
        detail: str | None = None,
        http_status: int | None = None,
        timeout: int | None = None,
    ) -> dict:
        """Build a structured error response dict."""
        if detail:
            human_msg = f"{SLACK_ERROR_MESSAGES.get(code, code)}: {detail}"
        elif timeout and code == "timeout":
            human_msg = f"Request timed out after {timeout} seconds. Slack may be experiencing issues."
        else:
            human_msg = SLACK_ERROR_MESSAGES.get(code, f"Internal error: {code}")
        self._slack_log("error", "api", f"{code}: {human_msg}")
        return {
            "ok": False,
            "data": None,
            "error": human_msg,
            "error_code": code,
            "http_status": http_status,
        }

    def _slack_log(self, level: str, component: str, message: str, **context) -> None:
        """Structured logging helper.

        Uses the component's ``self.log()`` if available (LangBuilder runtime),
        falling back to the module-level ``logger``.
        """
        formatted = f"[Slack:{component}] {message}"
        if context:
            ctx_str = " | ".join(f"{k}={v}" for k, v in context.items())
            formatted = f"{formatted} | {ctx_str}"

        # LangBuilder's Component base class provides self.log()
        lb_log = getattr(self, "log", None)
        if callable(lb_log):
            lb_log(formatted)
        else:
            getattr(logger, level, logger.info)(formatted)
