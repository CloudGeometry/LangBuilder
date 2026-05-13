"""Tests for LangWatchService._parse_trace() and _aggregate_with_metadata().

Covers all 12 acceptance criteria for F2-T4.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest
from langflow.services.langwatch.schemas import UsageQueryParams
from langflow.services.langwatch.service import MAX_PAGES, PAGE_SIZE, LangWatchService

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def service():
    svc = LangWatchService.__new__(LangWatchService)
    svc._db_session = MagicMock()
    svc._client = LangWatchService._create_httpx_client()
    return svc


SAMPLE_TRACE = {
    "trace_id": "trace_abc123",
    "metadata": {
        "labels": ["Flow: Customer Bot"],
        "user_id": "user-1",
    },
    "metrics": {
        "total_cost": 0.0055,
        "prompt_tokens": 100,
        "completion_tokens": 50,
    },
    "timestamps": {"started_at": 1742135520000},
    "spans": [{"span_id": "s1", "model": "gpt-4o", "metrics": {}}],
    "error": None,
}

SAMPLE_PARAMS = UsageQueryParams(
    from_date=date(2026, 1, 1),
    to_date=date(2026, 1, 31),
)


# ── AC1: _parse_trace is a @staticmethod returning dict | None ──────────────

def test_parse_trace_is_static_method():
    """AC1: _parse_trace is a @staticmethod."""
    # Can call without instance
    result = LangWatchService._parse_trace(SAMPLE_TRACE)
    assert isinstance(result, dict)


# ── AC2: Extracts flow_name from metadata.labels ────────────────────────────

def test_parse_trace_extracts_flow_name():
    """AC2: Extracts flow_name from metadata.labels entry starting with 'Flow: '."""
    trace = {
        "trace_id": "t1",
        "metadata": {"labels": ["Flow: Customer Bot"]},
        "metrics": {},
        "timestamps": {},
        "spans": [],
        "error": None,
    }
    result = LangWatchService._parse_trace(trace)
    assert result is not None
    assert result["flow_name"] == "Customer Bot"


def test_parse_trace_flow_name_none_when_no_flow_label():
    """AC2: flow_name is None when no 'Flow: ' label exists."""
    trace = {
        "trace_id": "t2",
        "metadata": {"labels": ["SomeOtherLabel"]},
        "metrics": {},
        "timestamps": {},
        "spans": [],
        "error": None,
    }
    result = LangWatchService._parse_trace(trace)
    assert result is not None
    assert result["flow_name"] is None


def test_parse_trace_flow_name_none_when_no_labels():
    """AC2: flow_name is None when metadata has no labels."""
    trace = {
        "trace_id": "t3",
        "metadata": {},
        "metrics": {},
        "timestamps": {},
        "spans": [],
        "error": None,
    }
    result = LangWatchService._parse_trace(trace)
    assert result is not None
    assert result["flow_name"] is None


# ── AC3: Extracts cost_usd from metrics.total_cost ──────────────────────────

def test_parse_trace_extracts_cost():
    """AC3: Extracts cost_usd from metrics.total_cost."""
    result = LangWatchService._parse_trace(SAMPLE_TRACE)
    assert result is not None
    assert result["cost_usd"] == 0.0055


def test_parse_trace_handles_null_cost():
    """AC3: Null total_cost maps to 0.0."""
    trace = {
        **SAMPLE_TRACE,
        "metrics": {"total_cost": None},
    }
    result = LangWatchService._parse_trace(trace)
    assert result is not None
    assert result["cost_usd"] == 0.0


def test_parse_trace_handles_missing_cost():
    """AC3: Missing total_cost maps to 0.0."""
    trace = {
        **SAMPLE_TRACE,
        "metrics": {},
    }
    result = LangWatchService._parse_trace(trace)
    assert result is not None
    assert result["cost_usd"] == 0.0


# ── AC4: Extracts prompt_tokens, completion_tokens ──────────────────────────

def test_parse_trace_extracts_tokens():
    """AC4: Extracts prompt_tokens and completion_tokens as int or None."""
    result = LangWatchService._parse_trace(SAMPLE_TRACE)
    assert result is not None
    assert result["prompt_tokens"] == 100
    assert result["completion_tokens"] == 50


def test_parse_trace_tokens_none_when_missing():
    """AC4: prompt_tokens and completion_tokens are None when not present."""
    trace = {**SAMPLE_TRACE, "metrics": {"total_cost": 0.001}}
    result = LangWatchService._parse_trace(trace)
    assert result is not None
    assert result["prompt_tokens"] is None
    assert result["completion_tokens"] is None


# ── AC5: Extracts model from first span with non-null model field ────────────

def test_parse_trace_extracts_model_from_first_span():
    """AC5: Extracts model from first span with a non-null model."""
    result = LangWatchService._parse_trace(SAMPLE_TRACE)
    assert result is not None
    assert result["model"] == "gpt-4o"


def test_parse_trace_model_skips_spans_without_model():
    """AC5: Skips spans with null model field."""
    trace = {
        **SAMPLE_TRACE,
        "spans": [
            {"span_id": "s1", "model": None, "metrics": {}},
            {"span_id": "s2", "model": "gpt-3.5-turbo", "metrics": {}},
        ],
    }
    result = LangWatchService._parse_trace(trace)
    assert result is not None
    assert result["model"] == "gpt-3.5-turbo"


def test_parse_trace_model_none_when_no_spans():
    """AC5: model is None when no spans have a model."""
    trace = {**SAMPLE_TRACE, "spans": []}
    result = LangWatchService._parse_trace(trace)
    assert result is not None
    assert result["model"] is None


# ── AC6: Returns None for malformed/unparseable traces ──────────────────────

def test_parse_trace_returns_none_for_none_input():
    """AC6: _parse_trace(None) returns None."""
    result = LangWatchService._parse_trace(None)
    assert result is None


def test_parse_trace_handles_empty_dict():
    """AC6: Empty dict is not None (parseable with defaults)."""
    result = LangWatchService._parse_trace({})
    assert result is not None


def test_parse_trace_returns_none_for_non_subscriptable():
    """AC6: Non-dict (string, int) returns None without crash."""
    assert LangWatchService._parse_trace("bad_input") is None
    assert LangWatchService._parse_trace(42) is None


# ── AC7: _aggregate_with_metadata groups traces by flow_name ───────────────

def test_aggregate_groups_by_flow_name(service):
    """AC7: Traces from same flow are grouped together."""
    traces = [
        {**SAMPLE_TRACE, "trace_id": "t1"},
        {**SAMPLE_TRACE, "trace_id": "t2"},
        {
            "trace_id": "t3",
            "metadata": {"labels": ["Flow: Bot Two"]},
            "metrics": {"total_cost": 0.001, "prompt_tokens": 50, "completion_tokens": 25},
            "timestamps": {"started_at": 1742135520000},
            "spans": [{"span_id": "s3", "model": "gpt-3.5-turbo", "metrics": {}}],
            "error": None,
        },
    ]
    result = service._aggregate_with_metadata(traces, SAMPLE_PARAMS)
    flow_names = [f.flow_name for f in result.flows]
    assert "Customer Bot" in flow_names
    assert "Bot Two" in flow_names
    # Customer Bot has 2 traces
    customer_bot = next(f for f in result.flows if f.flow_name == "Customer Bot")
    assert customer_bot.invocation_count == 2


# ── AC8: Skips traces where flow_name is None ───────────────────────────────

def test_aggregate_skips_traces_without_flow_label(service):
    """AC8: Traces with no 'Flow: ' label are not included in flows."""
    traces = [
        SAMPLE_TRACE,  # has "Flow: Customer Bot"
        {
            "trace_id": "t_no_flow",
            "metadata": {"labels": ["SomeOtherLabel"]},
            "metrics": {"total_cost": 9.99},
            "timestamps": {},
            "spans": [],
            "error": None,
        },
    ]
    result = service._aggregate_with_metadata(traces, SAMPLE_PARAMS)
    flow_names = [f.flow_name for f in result.flows]
    assert "Customer Bot" in flow_names
    # The unlabeled trace is not in any flow
    assert len(result.flows) == 1


# ── AC9: Returns UsageResponse with correct summary totals ─────────────────

def test_aggregate_computes_totals(service):
    """AC9: total_cost_usd, total_invocations, avg_cost, active_flow_count correct."""
    traces = [
        {**SAMPLE_TRACE, "trace_id": "t1", "metrics": {"total_cost": 0.002}},
        {**SAMPLE_TRACE, "trace_id": "t2", "metrics": {"total_cost": 0.003}},
        {
            "trace_id": "t3",
            "metadata": {"labels": ["Flow: Bot Two"]},
            "metrics": {"total_cost": 0.005},
            "timestamps": {},
            "spans": [],
            "error": None,
        },
    ]
    result = service._aggregate_with_metadata(traces, SAMPLE_PARAMS)
    assert result.summary.total_invocations == 3
    assert abs(result.summary.total_cost_usd - 0.010) < 1e-9
    assert result.summary.active_flow_count == 2
    expected_avg = 0.010 / 3
    assert abs(result.summary.avg_cost_per_invocation_usd - round(expected_avg, 6)) < 1e-9


def test_aggregate_returns_usage_response(service):
    """AC9: Returns a UsageResponse instance."""
    from langflow.services.langwatch.schemas import UsageResponse
    result = service._aggregate_with_metadata([SAMPLE_TRACE], SAMPLE_PARAMS)
    assert isinstance(result, UsageResponse)


# ── AC10: flow_usages sorted by total_cost_usd descending ──────────────────

def test_aggregate_flows_sorted_by_cost_descending(service):
    """AC10: flows list is sorted by total_cost_usd descending."""
    traces = [
        {
            "trace_id": "t1",
            "metadata": {"labels": ["Flow: Cheap Bot"]},
            "metrics": {"total_cost": 0.001},
            "timestamps": {},
            "spans": [],
            "error": None,
        },
        {
            "trace_id": "t2",
            "metadata": {"labels": ["Flow: Expensive Bot"]},
            "metrics": {"total_cost": 0.050},
            "timestamps": {},
            "spans": [],
            "error": None,
        },
        {
            "trace_id": "t3",
            "metadata": {"labels": ["Flow: Medium Bot"]},
            "metrics": {"total_cost": 0.010},
            "timestamps": {},
            "spans": [],
            "error": None,
        },
    ]
    result = service._aggregate_with_metadata(traces, SAMPLE_PARAMS)
    costs = [f.total_cost_usd for f in result.flows]
    assert costs == sorted(costs, reverse=True)
    assert result.flows[0].flow_name == "Expensive Bot"


# ── AC11: summary.truncated = True when len(traces) >= MAX_PAGES * PAGE_SIZE ─

def test_aggregate_truncated_flag_true_when_at_threshold(service):
    """AC11: summary.truncated=True when len(traces) >= MAX_PAGES * PAGE_SIZE."""
    threshold = MAX_PAGES * PAGE_SIZE
    # Create exactly threshold number of traces all with flow label
    trace_template = {
        "trace_id": "t_{}",
        "metadata": {"labels": ["Flow: Big Flow"]},
        "metrics": {"total_cost": 0.001},
        "timestamps": {},
        "spans": [],
        "error": None,
    }
    traces = [{**trace_template, "trace_id": f"t_{i}"} for i in range(threshold)]
    result = service._aggregate_with_metadata(traces, SAMPLE_PARAMS)
    assert result.summary.truncated is True


def test_aggregate_truncated_flag_false_below_threshold(service):
    """AC11: summary.truncated=False when len(traces) < MAX_PAGES * PAGE_SIZE."""
    traces = [SAMPLE_TRACE]
    result = service._aggregate_with_metadata(traces, SAMPLE_PARAMS)
    assert result.summary.truncated is False


# ── AC12: Handles empty traces list ─────────────────────────────────────────

def test_aggregate_empty_traces(service):
    """AC12: Empty input returns zero-summary UsageResponse."""
    result = service._aggregate_with_metadata([], SAMPLE_PARAMS)
    assert result.summary.total_cost_usd == 0.0
    assert result.summary.total_invocations == 0
    assert result.summary.avg_cost_per_invocation_usd == 0.0
    assert result.summary.active_flow_count == 0
    assert result.flows == []


def test_aggregate_empty_traces_date_range(service):
    """AC12: Empty input preserves date_range from params."""
    result = service._aggregate_with_metadata([], SAMPLE_PARAMS)
    assert result.summary.date_range.from_ == date(2026, 1, 1)
    assert result.summary.date_range.to == date(2026, 1, 31)
