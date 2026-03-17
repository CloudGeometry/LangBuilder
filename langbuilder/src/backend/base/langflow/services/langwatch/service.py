"""LangWatch service skeleton.

The public interface is defined here (F1-T5).  All method bodies raise
``NotImplementedError``; they will be filled in during Feature F2.

F2-T2 adds:
- ``_create_httpx_client()`` static factory method
- ``self._client`` stored in ``__init__``
- ``aclose()`` async method to close the client

F2-T4 adds:
- ``_parse_trace()`` static method
- ``_aggregate_with_metadata()`` instance method

F2-T5 adds:
- ``FlowMeta`` dataclass at module level
- ``_filter_by_ownership()`` async method
- Updated ``_aggregate_with_metadata()`` with optional ``flow_name_map`` parameter

F2-T6 adds:
- ``redis`` optional param to ``__init__``
- ``cache_ttl`` class attribute
- ``_build_cache_key()`` instance method
- Real async ``get_usage_summary()`` with cache-aside pattern
- Real async ``invalidate_cache()``

F2-T7 adds:
- Module-level ``_get_fernet()`` helper for key derivation
- ``_get_setting()`` instance method for GlobalSettings lookup
- Real async ``save_key()``, ``get_stored_key()``, ``get_key_status()``
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
from collections import defaultdict
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import NAMESPACE_DNS, UUID, uuid5

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends
from lfx.services.deps import injectable_session_scope

from langflow.services.deps import get_settings_service

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlmodel.ext.asyncio.session import AsyncSession

    from langflow.services.database.models.global_settings import GlobalSettings
    from langflow.services.langwatch.schemas import (
        FlowRunsQueryParams,
        FlowRunsResponse,
        KeyStatusResponse,
        UsageQueryParams,
        UsageResponse,
    )


logger = logging.getLogger(__name__)


MAX_PAGES: int = 10
PAGE_SIZE: int = 1000


# ── Encryption helper ─────────────────────────────────────────────────────────


def _get_fernet() -> Fernet:
    """Derive a Fernet instance from the application SECRET_KEY.

    Uses SHA-256 to convert the secret key to a valid 32-byte Fernet key.
    Matches the existing Variable model encryption pattern.

    Returns:
        Fernet: Configured Fernet instance for encryption/decryption.
    """
    settings_service = get_settings_service()
    secret_key: str = settings_service.auth_settings.SECRET_KEY.get_secret_value()
    key = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode()).digest())
    return Fernet(key)


# ── Domain types ──────────────────────────────────────────────────────────────


@dataclass
class FlowMeta:
    """Metadata for a flow resolved from the DB.

    Used by ``_filter_by_ownership()`` to carry real DB UUIDs and owner info
    into ``_aggregate_with_metadata()``.
    """

    flow_id: UUID
    user_id: UUID
    username: str


# ── Service class ─────────────────────────────────────────────────────────────


class LangWatchService:
    """Service for interacting with the LangWatch analytics API.

    All methods are stubs that raise ``NotImplementedError``.  Full
    implementations are added in Feature F2.
    """

    cache_ttl: int = 300  # 5 minutes

    def __init__(self, db_session: AsyncSession, redis: Redis | None = None) -> None:
        self._db_session = db_session
        self.redis = redis
        self._client: httpx.AsyncClient = self._create_httpx_client()

    # -- Client lifecycle ------------------------------------------------------

    @staticmethod
    def _create_httpx_client() -> httpx.AsyncClient:
        """Create a configured httpx.AsyncClient for LangWatch API calls.

        Configuration:
        - Base URL from LANGWATCH_ENDPOINT env var (default: https://app.langwatch.ai)
        - Timeouts: connect=5s, read=30s, write=10s, pool=5s
        - Connection limits: max_connections=20, max_keepalive_connections=10
        - Default Content-Type header: application/json

        Returns:
            httpx.AsyncClient: A configured async HTTP client.
        """
        base_url: str = os.getenv("LANGWATCH_ENDPOINT", "https://app.langwatch.ai")

        return httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(
                connect=5.0,
                read=30.0,
                write=10.0,
                pool=5.0,
            ),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30.0,
            ),
            headers={"Content-Type": "application/json"},
        )

    async def aclose(self) -> None:
        """Close the underlying httpx client and release connection pool resources."""
        await self._client.aclose()

    # -- LangWatch fetch -------------------------------------------------------

    async def _fetch_all_pages(
        self,
        api_key: str,
        start_date_ms: int,
        end_date_ms: int,
    ) -> list[dict]:
        """Fetch all pages of traces from LangWatch using scroll pagination.

        Args:
            api_key: The LangWatch API key for authentication.
            start_date_ms: Start of date range in epoch milliseconds.
            end_date_ms: End of date range in epoch milliseconds.

        Returns:
            List of raw trace dicts (all pages combined).
        """
        all_traces: list[dict] = []
        scroll_id: str | None = None
        headers = {"X-Auth-Token": api_key}

        for _page_num in range(MAX_PAGES):
            payload: dict = {
                "startDate": start_date_ms,
                "endDate": end_date_ms,
                "pageSize": PAGE_SIZE,
                "includeSpans": True,
            }
            if scroll_id:
                payload["scrollId"] = scroll_id

            response = await self._client.post(
                "/api/traces/search",
                json=payload,
                headers=headers,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                from langflow.services.langwatch.exceptions import (
                    LangWatchInvalidKeyError,
                    LangWatchUnavailableError,
                )
                if exc.response.status_code in (401, 403):
                    msg = f"LangWatch rejected the API key: {exc.response.status_code}"
                    raise LangWatchInvalidKeyError(msg) from exc
                msg = f"LangWatch API error: {exc.response.status_code}"
                raise LangWatchUnavailableError(msg) from exc
            data = response.json()

            page_traces = data.get("traces", [])
            all_traces.extend(page_traces)

            pagination = data.get("pagination", {})
            scroll_id = pagination.get("scrollId")

            # Stop conditions
            if not scroll_id:
                break
            if not page_traces:
                break

        return all_traces

    async def _fetch_from_langwatch(
        self,
        params: UsageQueryParams,
        api_key: str,
    ) -> list[dict]:
        """Fetch raw traces from LangWatch for the given query parameters.

        Converts UsageQueryParams to LangWatch API format and delegates
        to _fetch_all_pages for scroll-based pagination.

        Args:
            params: Query parameters (date range, filters).
            api_key: The LangWatch API key for authentication.

        Returns:
            List of raw trace dicts.
        """
        from datetime import datetime, timezone

        from_date = params.from_date
        to_date = params.to_date

        if from_date is not None and not isinstance(from_date, datetime):
            from_dt = datetime(from_date.year, from_date.month, from_date.day, tzinfo=timezone.utc)
        else:
            from_dt = from_date  # type: ignore[assignment]

        if to_date is not None and not isinstance(to_date, datetime):
            to_dt = datetime(to_date.year, to_date.month, to_date.day, tzinfo=timezone.utc)
        else:
            to_dt = to_date  # type: ignore[assignment]

        start_ms = int(from_dt.timestamp() * 1000) if from_dt else 0
        end_ms = (
            int(to_dt.timestamp() * 1000)
            if to_dt
            else int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        )

        all_traces = await self._fetch_all_pages(
            api_key=api_key,
            start_date_ms=start_ms,
            end_date_ms=end_ms,
        )

        # Filter to workflow-type traces only — a single flow execution creates N+1 traces
        # (1 workflow + N component traces). Only the workflow trace represents the full execution.
        # Guard: if spans aren't included (backward compat), keep traces with no spans.
        filtered = [
            t for t in all_traces
            if not t.get("spans") or any(s.get("type") == "workflow" for s in t["spans"])
        ]
        logger.debug(
            "Fetched %d traces from LangWatch (%d after workflow filter)",
            len(all_traces), len(filtered),
        )
        return filtered

    # -- Response parsing ------------------------------------------------------

    @staticmethod
    def _parse_trace(trace: dict) -> dict | None:
        """Extract key fields from a raw LangWatch trace dict.

        Args:
            trace: Raw trace dict from LangWatch API response.

        Returns:
            Simplified dict with extracted fields, or None if trace is malformed.
        """
        try:
            metadata = trace.get("metadata") or {}
            labels: list = metadata.get("labels") or []
            metrics = trace.get("metrics") or {}
            timestamps = trace.get("timestamps") or {}

            # Extract flow name from labels: "Flow: <name>"
            flow_name: str | None = next(
                (lbl[6:] for lbl in labels if isinstance(lbl, str) and lbl.startswith("Flow: ")),
                None,
            )

            # Fallback: extract from root workflow span name (OTEL SDK doesn't surface labels in API metadata)
            spans = trace.get("spans") or []
            if flow_name is None:
                for span in spans:
                    if span.get("type") == "workflow":
                        flow_name = span.get("name")
                        break

            # Cost: metrics.total_cost (float or null)
            cost = metrics.get("total_cost")
            cost_usd: float = float(cost) if cost is not None else 0.0

            # Tokens
            prompt_tokens = metrics.get("prompt_tokens")
            completion_tokens = metrics.get("completion_tokens")

            # Model (from first span — reuses `spans` from above)
            model: str | None = None
            for span in spans:
                if span.get("model"):
                    model = span["model"]
                    break

            # Timestamp
            started_ms = timestamps.get("started_at")
            started_at_ms: int | None = int(started_ms) if started_ms is not None else None

            return {
                "trace_id": trace.get("trace_id", ""),
                "flow_name": flow_name,
                "cost_usd": cost_usd,
                "prompt_tokens": int(prompt_tokens) if prompt_tokens is not None else None,
                "completion_tokens": int(completion_tokens) if completion_tokens is not None else None,
                "model": model,
                "started_at_ms": started_at_ms,
                "has_error": trace.get("error") is not None,
            }
        except (TypeError, ValueError, AttributeError):
            return None

    async def _filter_by_ownership(
        self,
        traces: list[dict],
        allowed_flow_ids: set[UUID],
    ) -> tuple[list[dict], dict[str, FlowMeta]]:
        """Filter traces to those belonging to allowed flows, with DB owner lookup.

        Queries the DB to resolve flow_ids → (flow_name, user_id, username).
        Filters traces by matching the "Flow: <name>" label pattern.

        Args:
            traces: Raw trace dicts from LangWatch.
            allowed_flow_ids: Set of flow UUIDs the caller is permitted to see.

        Returns:
            Tuple of (filtered_traces, flow_name_map) where:
              filtered_traces: traces whose flow_name is in the allowed set
              flow_name_map: dict mapping flow_name → FlowMeta(flow_id, user_id, username)
        """
        if not allowed_flow_ids:
            return [], {}

        from sqlmodel import select

        from langflow.services.database.models.flow.model import Flow
        from langflow.services.database.models.user.model import User

        # Query DB for flow metadata
        stmt = (
            select(Flow.id, Flow.name, Flow.user_id, User.username)
            .join(User, Flow.user_id == User.id, isouter=True)
            .where(Flow.id.in_(allowed_flow_ids))
        )
        result = await self._db_session.exec(stmt)
        rows = result.all()

        # Build name → FlowMeta map
        # NOTE: LangWatch trace labels only contain flow *names* (e.g., "Flow: My Bot"),
        # not flow IDs. When two flows share a name, we cannot perfectly disambiguate.
        # Heuristic: prefer the flow whose ID is in allowed_flow_ids; tie-break by
        # most recently created.
        flow_name_map: dict[str, FlowMeta] = {}
        for row in rows:
            meta = FlowMeta(
                flow_id=row.id,
                user_id=row.user_id or UUID(int=0),
                username=row.username or "",
            )
            existing = flow_name_map.get(row.name)
            if existing is None:
                flow_name_map[row.name] = meta
            else:
                # Collision: two flows share a name.
                # Prefer the one whose ID is in allowed_flow_ids.
                new_allowed = row.id in allowed_flow_ids
                old_allowed = existing.flow_id in allowed_flow_ids
                if new_allowed and not old_allowed:
                    flow_name_map[row.name] = meta
                elif new_allowed and old_allowed:
                    # Both allowed (admin view) — prefer most recently created.
                    if hasattr(row, "created_at") and row.created_at and (
                        not hasattr(existing, "created_at")
                        or not getattr(existing, "created_at", None)
                        or row.created_at > existing.created_at
                    ):
                        flow_name_map[row.name] = meta

        allowed_names = set(flow_name_map.keys())

        # Filter traces
        filtered: list[dict] = []
        for trace in traces:
            metadata = trace.get("metadata") or {}
            labels: list = metadata.get("labels") or []
            flow_name = next(
                (lbl[6:] for lbl in labels if isinstance(lbl, str) and lbl.startswith("Flow: ")),
                None,
            )
            # Fallback: root workflow span name (OTEL SDK doesn't surface labels in API metadata)
            if flow_name is None:
                for span in trace.get("spans", []):
                    if span.get("type") == "workflow":
                        flow_name = span.get("name")
                        break
            if flow_name in allowed_names:
                filtered.append(trace)

        dropped = len(traces) - len(filtered)
        if dropped:
            logger.debug(
                "Ownership filter: kept %d of %d traces (%d dropped, no flow match)",
                len(filtered), len(traces), dropped,
            )

        return filtered, flow_name_map

    def _aggregate_with_metadata(
        self,
        traces: list[dict],
        params: UsageQueryParams,
        flow_name_map: dict[str, FlowMeta] | None = None,
    ) -> UsageResponse:
        """Aggregate raw traces into a UsageResponse.

        Groups traces by flow_name (extracted from LangWatch labels).
        If ``flow_name_map`` is provided (from ``_filter_by_ownership``), real DB
        UUIDs and owner info are used; otherwise placeholders are used.

        Args:
            traces: Raw trace dicts from LangWatch (already filtered by F2-T5 if applicable).
            params: Query parameters for date range metadata.
            flow_name_map: Optional mapping of flow_name → FlowMeta from DB lookup.

        Returns:
            UsageResponse with per-flow aggregates and summary totals.
        """
        from langflow.services.langwatch.schemas import (
            DateRange,
            FlowUsage,
            UsageResponse,
            UsageSummary,
        )

        # Parse each trace
        parsed = [p for t in traces if (p := self._parse_trace(t)) is not None]

        # Group by flow_name
        groups: dict[str | None, list[dict]] = defaultdict(list)
        for p in parsed:
            groups[p["flow_name"]].append(p)

        # Build per-flow aggregates
        nil_uuid = UUID(int=0)
        flow_usages: list[FlowUsage] = []

        for flow_name, flow_traces in groups.items():
            if flow_name is None:
                continue  # Skip traces with no flow label

            total_cost = sum(t["cost_usd"] for t in flow_traces)
            invocation_count = len(flow_traces)
            avg_cost = total_cost / invocation_count if invocation_count > 0 else 0.0

            # Look up real DB data if available
            meta = flow_name_map.get(flow_name) if flow_name_map else None
            flow_id = meta.flow_id if meta else uuid5(NAMESPACE_DNS, f"langbuilder.flow.{flow_name}")
            owner_user_id = meta.user_id if meta else nil_uuid
            owner_username = meta.username if meta else ""

            flow_usages.append(
                FlowUsage(
                    flow_id=flow_id,
                    flow_name=flow_name,
                    total_cost_usd=round(total_cost, 6),
                    invocation_count=invocation_count,
                    avg_cost_per_invocation_usd=round(avg_cost, 6),
                    owner_user_id=owner_user_id,
                    owner_username=owner_username,
                )
            )

        # Sort by total cost descending
        flow_usages.sort(key=lambda f: f.total_cost_usd, reverse=True)

        # Summary totals
        total_cost_usd = sum(f.total_cost_usd for f in flow_usages)
        total_invocations = sum(f.invocation_count for f in flow_usages)
        avg_cost = total_cost_usd / total_invocations if total_invocations > 0 else 0.0

        summary = UsageSummary(
            total_cost_usd=round(total_cost_usd, 6),
            total_invocations=total_invocations,
            avg_cost_per_invocation_usd=round(avg_cost, 6),
            active_flow_count=len(flow_usages),
            date_range=DateRange(
                from_=params.from_date,
                to=params.to_date,
            ),
            cached=False,
            truncated=len(traces) >= MAX_PAGES * PAGE_SIZE,
        )

        return UsageResponse(summary=summary, flows=flow_usages)

    # -- Cache helpers ---------------------------------------------------------

    def _build_cache_key(
        self,
        params: UsageQueryParams,
        allowed_flow_ids: set[UUID],
        org_id: str,
        *,
        is_admin: bool = False,
    ) -> str:
        """Build a cache key scoped to org + sub_view + user filter + date range.

        Key format: usage:{org_id}:{sub_view}:{user_scope}:{date_hash}

        Args:
            params: Query parameters containing sub_view, user_id, and date range.
            allowed_flow_ids: Set of flow UUIDs the caller is permitted to see.
            org_id: Organisation identifier for key scoping.
            is_admin: Whether the requesting user is an admin (superuser).

        Returns:
            A deterministic cache key string.
        """
        # User scope: specific UUID for filtered view, role-aware scoping for empty sets
        if params.user_id:
            user_scope = str(params.user_id)
        elif is_admin and len(allowed_flow_ids) == 0:
            user_scope = "admin:all"
        elif len(allowed_flow_ids) == 0:
            user_scope = "user:none"
        else:
            user_scope = "user"

        # Date hash: compact representation of date range
        date_str = f"{params.from_date}:{params.to_date}"
        date_hash = hashlib.sha256(date_str.encode()).hexdigest()[:12]

        return f"usage:{org_id}:{params.sub_view}:{user_scope}:{date_hash}"

    # -- Usage summary ---------------------------------------------------------

    async def get_usage_summary(
        self,
        params: UsageQueryParams,
        allowed_flow_ids: set[UUID],
        api_key: str,
        org_id: str = "default",
        *,
        is_admin: bool = False,
    ) -> UsageResponse:
        """Return aggregated cost/invocation data for the given filters.

        Implements a Redis cache-aside pattern:
        1. Try to read from Redis cache
        2. On cache miss (or Redis error), fetch from LangWatch
        3. Write result to Redis cache
        4. Return result

        Args:
            params: Query parameters (date range, sub_view, user_id filter).
            allowed_flow_ids: Set of flow UUIDs the caller is permitted to see.
            api_key: The LangWatch API key for authentication.
            org_id: Organisation identifier for cache key scoping.
            is_admin: Whether the requesting user is an admin (superuser).

        Returns:
            UsageResponse with per-flow aggregates and summary totals.
        """
        cache_key = self._build_cache_key(params, allowed_flow_ids, org_id, is_admin=is_admin)

        # 1. Try cache read (with graceful degradation)
        if self.redis is not None:
            try:
                cached_value = await self.redis.get(cache_key)
                if cached_value:
                    from langflow.services.langwatch.schemas import UsageResponse as _UsageResponse
                    data = _UsageResponse.model_validate_json(cached_value)
                    data.summary.cached = True
                    try:
                        ttl = await self.redis.ttl(cache_key)
                        data.summary.cache_age_seconds = max(0, self.cache_ttl - ttl)
                    except (ConnectionError, OSError, TimeoutError):
                        logger.debug("Could not fetch TTL for cache key %s", cache_key)
                    return data
            except (ConnectionError, OSError, TimeoutError):
                logger.warning("Redis unavailable for cache read — proceeding uncached")

        # 2. Cache miss — fetch from LangWatch
        try:
            raw_data = await self._fetch_from_langwatch(params, api_key)
        except httpx.TimeoutException as exc:
            from langflow.services.langwatch.exceptions import LangWatchUnavailableError
            msg = f"LangWatch request timed out: {exc}"
            raise LangWatchUnavailableError(msg) from exc
        except httpx.TransportError as exc:
            from langflow.services.langwatch.exceptions import LangWatchUnavailableError
            msg = f"LangWatch connection error: {exc}"
            raise LangWatchUnavailableError(msg) from exc
        filtered, flow_map = await self._filter_by_ownership(raw_data, allowed_flow_ids)
        aggregated = self._aggregate_with_metadata(filtered, params, flow_name_map=flow_map)

        # 3. Write to cache (with graceful degradation)
        if self.redis is not None:
            try:
                await self.redis.setex(
                    cache_key,
                    self.cache_ttl,
                    aggregated.model_dump_json(by_alias=True),
                )
            except (ConnectionError, OSError, TimeoutError):
                logger.warning("Redis unavailable for cache write — result not cached")

        return aggregated

    # -- Flow runs -------------------------------------------------------------

    async def fetch_flow_runs(
        self,
        flow_id: UUID,
        flow_name: str,
        query: FlowRunsQueryParams,
        api_key: str,
    ) -> FlowRunsResponse:
        """Fetch per-run detail for a specific flow from LangWatch.

        Retrieves individual trace/run data for the given flow from the
        LangWatch API, filtered by flow name label and date range.

        Ownership filtering is handled by the router before calling this method.

        Args:
            flow_id: The UUID of the flow to fetch runs for.
            flow_name: The name of the flow (used to match LangWatch labels).
            query: Query parameters (date range, limit).
            api_key: The LangWatch API key for authentication.

        Returns:
            FlowRunsResponse with per-run details and total count.

        Raises:
            LangWatchUnavailableError: On network failure or timeout.
        """
        from langflow.services.langwatch.exceptions import LangWatchUnavailableError
        from langflow.services.langwatch.schemas import FlowRunsResponse, RunDetail

        # Convert query dates to milliseconds for the LangWatch API
        from_dt = query.from_date
        to_dt = query.to_date

        if from_dt is not None and not isinstance(from_dt, datetime):
            from_datetime = datetime(from_dt.year, from_dt.month, from_dt.day, tzinfo=timezone.utc)
        else:
            from_datetime = from_dt  # type: ignore[assignment]

        if to_dt is not None and not isinstance(to_dt, datetime):
            to_datetime = datetime(to_dt.year, to_dt.month, to_dt.day, tzinfo=timezone.utc)
        else:
            to_datetime = to_dt  # type: ignore[assignment]

        start_ms = int(from_datetime.timestamp() * 1000) if from_datetime else 0
        end_ms = (
            int(to_datetime.timestamp() * 1000)
            if to_datetime
            else int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        )

        # Fetch all pages from LangWatch
        try:
            all_traces = await self._fetch_all_pages(
                api_key=api_key,
                start_date_ms=start_ms,
                end_date_ms=end_ms,
            )
        except httpx.TimeoutException as exc:
            msg = f"LangWatch request timed out: {exc}"
            raise LangWatchUnavailableError(msg) from exc
        except httpx.TransportError as exc:
            msg = f"LangWatch connection error: {exc}"
            raise LangWatchUnavailableError(msg) from exc

        # Filter traces to only those belonging to the target flow (by flow name label)
        flow_label = f"Flow: {flow_name}"
        flow_traces: list[dict] = []
        for trace in all_traces:
            metadata = trace.get("metadata") or {}
            labels: list = metadata.get("labels") or []
            if flow_label in labels:
                flow_traces.append(trace)

        # Parse traces into RunDetail objects
        run_details: list[RunDetail] = []
        for trace in flow_traces:
            parsed = self._parse_trace(trace)
            if parsed is None:
                continue

            timestamps = trace.get("timestamps") or {}
            started_ms_val = timestamps.get("started_at")
            if started_ms_val is not None:
                started_at = datetime.fromtimestamp(int(started_ms_val) / 1000.0, tz=timezone.utc)
            else:
                started_at = datetime.now(tz=timezone.utc)

            metrics = trace.get("metrics") or {}
            duration_ms = metrics.get("total_time_ms")

            run_status = "error" if trace.get("error") is not None else "success"

            prompt_tokens = parsed["prompt_tokens"]
            completion_tokens = parsed["completion_tokens"]
            if prompt_tokens is not None or completion_tokens is not None:
                total_tokens: int | None = (prompt_tokens or 0) + (completion_tokens or 0)
            else:
                total_tokens = None

            run_details.append(
                RunDetail(
                    run_id=parsed["trace_id"],
                    started_at=started_at,
                    cost_usd=parsed["cost_usd"],
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    model=parsed["model"],
                    duration_ms=int(duration_ms) if duration_ms is not None else None,
                    status=run_status,  # type: ignore[arg-type]
                )
            )

        # Sort by started_at descending (most recent first)
        run_details.sort(key=lambda r: r.started_at, reverse=True)

        # Apply limit
        total_count = len(run_details)
        run_details = run_details[: query.limit]

        return FlowRunsResponse(
            flow_id=flow_id,
            flow_name=flow_name,
            runs=run_details,
            total_runs_in_period=total_count,
        )

    # -- Key management --------------------------------------------------------

    async def _get_setting(self, key: str) -> GlobalSettings | None:
        """Retrieve a GlobalSettings row by key.

        Args:
            key: The settings key to look up (e.g. "LANGWATCH_API_KEY").

        Returns:
            The GlobalSettings row, or None if not found.
        """
        from sqlmodel import select

        from langflow.services.database.models.global_settings import GlobalSettings

        result = await self._db_session.execute(
            select(GlobalSettings).where(GlobalSettings.key == key).limit(1)
        )
        return result.scalar_one_or_none()

    async def save_key(self, api_key: str, admin_user_id: UUID) -> None:
        """Encrypt and save the LangWatch API key to GlobalSettings.

        Invalidates the usage cache after saving (new key may access different org).
        Logs a redacted preview — never logs the full key value.

        Args:
            api_key: The plaintext LangWatch API key to encrypt and store.
            admin_user_id: UUID of the admin user performing the operation.
        """
        from langflow.services.database.models.global_settings import GlobalSettings

        f = _get_fernet()
        encrypted_value = f.encrypt(api_key.encode()).decode()

        existing = await self._get_setting("LANGWATCH_API_KEY")
        now = datetime.now(tz=timezone.utc)

        if existing:
            existing.value = encrypted_value
            existing.is_encrypted = True
            existing.updated_at = now
            existing.updated_by = admin_user_id
            self._db_session.add(existing)
        else:
            setting = GlobalSettings(
                key="LANGWATCH_API_KEY",
                value=encrypted_value,
                is_encrypted=True,
                updated_by=admin_user_id,
            )
            self._db_session.add(setting)

        await self._db_session.commit()

        # Invalidate cache — new key may access different data
        await self.invalidate_cache()

        _preview_len = 3
        safe_preview = f"****{api_key[-_preview_len:]}" if len(api_key) > _preview_len else "****"
        logger.info("LangWatch API key saved. Preview: %s", safe_preview)

    async def get_stored_key(self) -> str | None:
        """Retrieve and decrypt the stored LangWatch API key.

        Returns None if no key is stored or if decryption fails
        (e.g., SECRET_KEY rotated).

        Returns:
            Decrypted plaintext key, or None if unavailable.
        """
        setting = await self._get_setting("LANGWATCH_API_KEY")
        if not setting:
            return None
        if not setting.is_encrypted:
            # Plaintext key (legacy / misconfigured) — return as-is
            return setting.value
        try:
            f = _get_fernet()
            return f.decrypt(setting.value.encode()).decode()
        except InvalidToken:
            logger.warning("Failed to decrypt LangWatch API key — SECRET_KEY may have changed")
            return None

    async def get_key_status(self) -> KeyStatusResponse:
        """Return whether a key is configured, with a redacted preview.

        Returns:
            KeyStatusResponse with has_key, optional key_preview, and configured_at.
        """
        from langflow.services.langwatch.schemas import KeyStatusResponse

        setting = await self._get_setting("LANGWATCH_API_KEY")
        if not setting:
            return KeyStatusResponse(has_key=False)

        # Try to get the decrypted key for preview
        decrypted = await self.get_stored_key()
        if decrypted is None:
            return KeyStatusResponse(has_key=False)

        _preview_len = 3
        preview = f"****{decrypted[-_preview_len:]}" if len(decrypted) > _preview_len else "****"
        return KeyStatusResponse(
            has_key=True,
            key_preview=preview,
            configured_at=setting.updated_at,
        )

    async def validate_key(self, api_key: str) -> bool:
        """Test an API key against LangWatch before saving.

        Makes a POST request to the LangWatch traces/search endpoint using
        the provided key in the X-Auth-Token header.

        Args:
            api_key: The LangWatch API key to validate.

        Returns:
            True if the key is accepted (200), False if rejected (401/403).

        Raises:
            ValueError: If api_key is empty or whitespace-only.
            LangWatchConnectionError: If the request fails due to a network
                error or timeout.
        """
        from langflow.services.langwatch.exceptions import LangWatchConnectionError

        if not api_key or not api_key.strip():
            msg = "api_key must be a non-empty string"
            raise ValueError(msg)

        headers = {"X-Auth-Token": api_key}
        # Minimal valid request — LangWatch requires startDate/endDate
        now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        payload = {
            "startDate": now_ms - 3600000,  # 1 hour ago
            "endDate": now_ms,
            "pageSize": 1,
        }

        try:
            response = await self._client.post(
                "/api/traces/search",
                headers=headers,
                json=payload,
            )
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            msg = f"Failed to connect to LangWatch API: {exc}"
            raise LangWatchConnectionError(msg) from exc

        # 200 = valid key with data, 400 = valid key but bad request shape (still authenticated)
        if response.status_code in (200, 400):  # noqa: PLR2004
            return True
        if response.status_code in (401, 403):
            return False

        logger.debug(
            "LangWatch key validation received unexpected status %d",
            response.status_code,
        )
        return False

    # -- Cache -----------------------------------------------------------------

    async def invalidate_cache(self) -> None:
        """Invalidate the Redis cache for usage data.

        Deletes all keys matching ``usage:*``.  Called when the LangWatch API
        key is updated or when a manual cache flush is requested.

        Gracefully handles Redis unavailability — logs a warning and returns.
        """
        if self.redis is None:
            return
        try:
            keys = await self.redis.keys("usage:*")
            if keys:
                await self.redis.delete(*keys)
                logger.info("Invalidated %d usage cache entries", len(keys))
        except (ConnectionError, OSError, TimeoutError):
            logger.warning("Redis unavailable — could not invalidate usage cache")


# ── DI factory ────────────────────────────────────────────────────────────────


async def get_langwatch_service(
    session: AsyncSession = Depends(injectable_session_scope),
) -> AsyncGenerator[LangWatchService, None]:
    """FastAPI dependency that provides a ``LangWatchService`` instance.

    Yields the service and closes the underlying httpx client on teardown,
    preventing connection leaks.

    Usage in a router::

        @router.get("/usage/")
        async def usage_endpoint(
            svc: LangWatchService = Depends(get_langwatch_service),
        ):
            ...
    """
    # NOTE: get_redis_client does not exist in lfx.services.deps — Redis caching is
    # currently non-functional. All requests hit the LangWatch API directly. The
    # cache-aside pattern in get_usage_summary gracefully no-ops when self.redis is None.
    # TODO(redis): Implement get_redis_client or replace with an alternative cache backend.
    redis_client = None
    try:
        from lfx.services.deps import get_redis_client  # type: ignore[import]
        redis_client = get_redis_client()
    except (ImportError, AttributeError):
        pass  # Redis is optional — service degrades gracefully without it
    svc = LangWatchService(db_session=session, redis=redis_client)
    try:
        yield svc
    finally:
        await svc.aclose()
