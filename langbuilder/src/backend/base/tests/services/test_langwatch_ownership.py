"""Tests for LangWatchService._filter_by_ownership() and updated _aggregate_with_metadata().

Covers all 11 acceptance criteria for F2-T5.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from langflow.services.langwatch.schemas import UsageQueryParams
from langflow.services.langwatch.service import FlowMeta, LangWatchService

# ── Fixtures ──────────────────────────────────────────────────────────────────

FLOW_UUID_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_UUID_A = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
FLOW_UUID_B = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
USER_UUID_B = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


def make_mock_db_result(rows):
    mock_result = MagicMock()
    mock_result.all.return_value = rows
    return mock_result


def make_flow_row(flow_id, name, user_id, username):
    row = MagicMock()
    row.id = flow_id
    row.name = name
    row.user_id = user_id
    row.username = username
    return row


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def make_service(mock_db):
    svc = LangWatchService.__new__(LangWatchService)
    svc._db_session = mock_db
    svc._client = LangWatchService._create_httpx_client()
    return svc


@pytest.fixture
def service():
    svc = LangWatchService.__new__(LangWatchService)
    svc._db_session = MagicMock()
    svc._client = LangWatchService._create_httpx_client()
    return svc


SAMPLE_PARAMS = UsageQueryParams(
    from_date=date(2026, 1, 1),
    to_date=date(2026, 1, 31),
)


def make_trace(flow_name: str | None, cost: float = 0.001, trace_id: str = "t1") -> dict:
    labels = [f"Flow: {flow_name}"] if flow_name else []
    return {
        "trace_id": trace_id,
        "metadata": {"labels": labels},
        "metrics": {"total_cost": cost},
        "timestamps": {"started_at": 1742135520000},
        "spans": [],
        "error": None,
    }


# ── AC1: FlowMeta dataclass defined at module level ──────────────────────────

def test_flowmeta_dataclass_fields():
    """AC1: FlowMeta has flow_id, user_id, username fields."""
    meta = FlowMeta(
        flow_id=FLOW_UUID_A,
        user_id=USER_UUID_A,
        username="alice",
    )
    assert meta.flow_id == FLOW_UUID_A
    assert meta.user_id == USER_UUID_A
    assert meta.username == "alice"


def test_flowmeta_is_importable_from_service_module():
    """AC1: FlowMeta is importable from service module."""
    from langflow.services.langwatch.service import FlowMeta as FlowMetaClass
    assert FlowMetaClass is not None


# ── AC2: _filter_by_ownership is an async method ────────────────────────────

def test_filter_by_ownership_is_async():
    """AC2: _filter_by_ownership is a coroutine function."""
    import inspect
    assert inspect.iscoroutinefunction(LangWatchService._filter_by_ownership)


# ── AC3: Returns ([], {}) immediately when allowed_flow_ids is empty ─────────

@pytest.mark.asyncio
async def test_filter_empty_allowed_ids(make_service):
    """AC3: Returns ([], {}) immediately when allowed_flow_ids is empty."""
    traces = [make_trace("Bot A")]
    filtered, name_map = await make_service._filter_by_ownership(traces, set())
    assert filtered == []
    assert name_map == {}
    # DB should NOT be queried
    make_service._db_session.exec.assert_not_called()


# ── AC4: Queries DB for Flow records where id IN allowed_flow_ids ─────────────

@pytest.mark.asyncio
async def test_filter_queries_db_with_allowed_ids(mock_db, make_service):
    """AC4: Queries the DB when allowed_flow_ids is non-empty."""
    row = make_flow_row(FLOW_UUID_A, "Bot A", USER_UUID_A, "alice")
    mock_db.exec = AsyncMock(return_value=make_mock_db_result([row]))

    await make_service._filter_by_ownership([], {FLOW_UUID_A})
    mock_db.exec.assert_called_once()


# ── AC5: Builds flow_name_map: dict[str, FlowMeta] ───────────────────────────

@pytest.mark.asyncio
async def test_filter_builds_correct_name_map(mock_db, make_service):
    """AC5: flow_name_map has correct FlowMeta values."""
    row = make_flow_row(FLOW_UUID_A, "Bot A", USER_UUID_A, "alice")
    mock_db.exec = AsyncMock(return_value=make_mock_db_result([row]))

    _, name_map = await make_service._filter_by_ownership([], {FLOW_UUID_A})

    assert "Bot A" in name_map
    meta = name_map["Bot A"]
    assert meta.flow_id == FLOW_UUID_A
    assert meta.user_id == USER_UUID_A
    assert meta.username == "alice"


# ── AC6: Filters traces by "Flow: <name>" label matching a key in flow_name_map

@pytest.mark.asyncio
async def test_filter_keeps_matching_traces(mock_db, make_service):
    """AC6: Keeps traces whose flow_name is in the DB result."""
    row = make_flow_row(FLOW_UUID_A, "Bot A", USER_UUID_A, "alice")
    mock_db.exec = AsyncMock(return_value=make_mock_db_result([row]))

    traces = [make_trace("Bot A", trace_id="t1")]
    filtered, _ = await make_service._filter_by_ownership(traces, {FLOW_UUID_A})

    assert len(filtered) == 1
    assert filtered[0]["trace_id"] == "t1"


@pytest.mark.asyncio
async def test_filter_drops_unmatched_traces(mock_db, make_service):
    """AC6: Drops traces whose flow_name is NOT in allowed set."""
    row = make_flow_row(FLOW_UUID_A, "Bot A", USER_UUID_A, "alice")
    mock_db.exec = AsyncMock(return_value=make_mock_db_result([row]))

    traces = [
        make_trace("Bot A", trace_id="t1"),
        make_trace("Bot B", trace_id="t2"),  # NOT in allowed
        make_trace(None, trace_id="t3"),       # No flow label
    ]
    filtered, _ = await make_service._filter_by_ownership(traces, {FLOW_UUID_A})

    assert len(filtered) == 1
    assert filtered[0]["trace_id"] == "t1"


# ── AC7: Returns tuple (filtered_traces, flow_name_map) ──────────────────────

@pytest.mark.asyncio
async def test_filter_returns_tuple(mock_db, make_service):
    """AC7: Returns a tuple of (list, dict)."""
    row = make_flow_row(FLOW_UUID_A, "Bot A", USER_UUID_A, "alice")
    mock_db.exec = AsyncMock(return_value=make_mock_db_result([row]))

    result = await make_service._filter_by_ownership([], {FLOW_UUID_A})
    assert isinstance(result, tuple)
    assert len(result) == 2
    filtered, name_map = result
    assert isinstance(filtered, list)
    assert isinstance(name_map, dict)


# ── AC (edge case): Handles Flow with null user_id ───────────────────────────

@pytest.mark.asyncio
async def test_filter_handles_null_user(mock_db, make_service):
    """AC: Flow with user_id=None gets UUID(int=0) and empty username."""
    row = make_flow_row(FLOW_UUID_A, "Bot A", None, None)
    mock_db.exec = AsyncMock(return_value=make_mock_db_result([row]))

    _, name_map = await make_service._filter_by_ownership([], {FLOW_UUID_A})

    assert "Bot A" in name_map
    meta = name_map["Bot A"]
    assert meta.flow_id == FLOW_UUID_A
    assert meta.user_id == UUID(int=0)
    assert meta.username == ""


# ── AC8: _aggregate_with_metadata accepts optional flow_name_map ─────────────

def test_aggregate_accepts_optional_flow_name_map_param():
    """AC8: _aggregate_with_metadata can be called with flow_name_map=None."""
    import inspect
    sig = inspect.signature(LangWatchService._aggregate_with_metadata)
    assert "flow_name_map" in sig.parameters
    param = sig.parameters["flow_name_map"]
    assert param.default is None


# ── AC9: When flow_name_map provided, uses real flow_id and owner info ────────

def test_aggregate_uses_real_flow_id_when_map_provided(service):
    """AC9: When flow_name_map is provided, uses real flow_id from map."""
    real_flow_id = FLOW_UUID_A
    real_user_id = USER_UUID_A
    meta = FlowMeta(flow_id=real_flow_id, user_id=real_user_id, username="alice")
    flow_name_map = {"Customer Bot": meta}

    traces = [make_trace("Customer Bot", cost=0.005)]
    result = service._aggregate_with_metadata(traces, SAMPLE_PARAMS, flow_name_map=flow_name_map)

    assert len(result.flows) == 1
    flow = result.flows[0]
    assert flow.flow_id == real_flow_id
    assert flow.owner_user_id == real_user_id
    assert flow.owner_username == "alice"


# ── AC10: When flow_name_map is None, falls back to uuid5-derived flow_id ────

def test_aggregate_falls_back_when_no_map(service):
    """AC10: When flow_name_map is None, uses uuid5-derived flow_id."""
    from uuid import NAMESPACE_DNS, uuid5

    traces = [make_trace("Customer Bot", cost=0.005)]
    result = service._aggregate_with_metadata(traces, SAMPLE_PARAMS, flow_name_map=None)

    assert len(result.flows) == 1
    flow = result.flows[0]
    expected_id = uuid5(NAMESPACE_DNS, "langbuilder.flow.Customer Bot")
    assert flow.flow_id == expected_id
    assert flow.owner_user_id == UUID(int=0)
    assert flow.owner_username == ""


# ── AC11: All existing tests still pass (verified by running full suite) ──────

def test_aggregate_backward_compat_no_map_param(service):
    """AC11: _aggregate_with_metadata can be called WITHOUT flow_name_map (backward compat)."""
    traces = [make_trace("My Flow", cost=0.001)]
    # Should not raise
    result = service._aggregate_with_metadata(traces, SAMPLE_PARAMS)
    assert len(result.flows) == 1
    assert result.flows[0].flow_name == "My Flow"
