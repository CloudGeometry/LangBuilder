"""Tests for langwatch Pydantic schemas (F1-T4)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from langflow.services.langwatch.schemas import (
    DateRange,
    FlowRunsQueryParams,
    FlowRunsResponse,
    FlowUsage,
    KeyStatusResponse,
    RunDetail,
    SaveKeyResponse,
    SaveLangWatchKeyRequest,
    UsageQueryParams,
    UsageResponse,
    UsageSummary,
)


# ── SaveLangWatchKeyRequest ───────────────────────────────────────────────────

class TestSaveLangWatchKeyRequest:
    def test_valid_key(self):
        req = SaveLangWatchKeyRequest(api_key="abc123")
        assert req.api_key == "abc123"

    def test_empty_key_fails(self):
        with pytest.raises(ValidationError):
            SaveLangWatchKeyRequest(api_key="")

    def test_key_too_long_fails(self):
        with pytest.raises(ValidationError):
            SaveLangWatchKeyRequest(api_key="x" * 501)

    def test_max_length_key(self):
        req = SaveLangWatchKeyRequest(api_key="x" * 500)
        assert len(req.api_key) == 500

    def test_min_length_key(self):
        req = SaveLangWatchKeyRequest(api_key="a")
        assert req.api_key == "a"


# ── UsageQueryParams ──────────────────────────────────────────────────────────

class TestUsageQueryParams:
    def test_defaults(self):
        params = UsageQueryParams()
        assert params.from_date is None
        assert params.to_date is None
        assert params.user_id is None
        assert params.sub_view == "flows"

    def test_sub_view_default_literal(self):
        params = UsageQueryParams()
        assert params.sub_view == "flows"

    def test_sub_view_mcp(self):
        params = UsageQueryParams(sub_view="mcp")
        assert params.sub_view == "mcp"

    def test_sub_view_invalid(self):
        with pytest.raises(ValidationError):
            UsageQueryParams(sub_view="invalid")

    def test_with_dates_and_user_id(self):
        uid = uuid4()
        params = UsageQueryParams(
            from_date=date(2026, 1, 1),
            to_date=date(2026, 3, 1),
            user_id=uid,
        )
        assert params.from_date == date(2026, 1, 1)
        assert params.to_date == date(2026, 3, 1)
        assert params.user_id == uid


# ── FlowRunsQueryParams ───────────────────────────────────────────────────────

class TestFlowRunsQueryParams:
    def test_defaults(self):
        params = FlowRunsQueryParams()
        assert params.limit == 10
        assert params.from_date is None
        assert params.to_date is None

    def test_limit_min(self):
        params = FlowRunsQueryParams(limit=1)
        assert params.limit == 1

    def test_limit_max(self):
        params = FlowRunsQueryParams(limit=50)
        assert params.limit == 50

    def test_limit_below_min_fails(self):
        with pytest.raises(ValidationError):
            FlowRunsQueryParams(limit=0)

    def test_limit_above_max_fails(self):
        with pytest.raises(ValidationError):
            FlowRunsQueryParams(limit=51)


# ── DateRange ─────────────────────────────────────────────────────────────────

class TestDateRange:
    def test_defaults(self):
        dr = DateRange()
        assert dr.from_ is None
        assert dr.to is None

    def test_alias_serialization(self):
        dr = DateRange(from_=date(2026, 3, 1))
        dumped = dr.model_dump(by_alias=True)
        assert "from" in dumped
        assert dumped["from"] == date(2026, 3, 1)
        assert "to" in dumped
        assert dumped["to"] is None

    def test_populate_by_name(self):
        # Can set via Python name (from_) when populate_by_name=True
        dr = DateRange(from_=date(2026, 1, 1))
        assert dr.from_ == date(2026, 1, 1)

    def test_alias_in_dump_by_alias(self):
        dr = DateRange(from_=date(2026, 3, 1), to=date(2026, 3, 31))
        dumped = dr.model_dump(by_alias=True)
        assert dumped == {"from": date(2026, 3, 1), "to": date(2026, 3, 31)}


# ── UsageSummary ──────────────────────────────────────────────────────────────

class TestUsageSummary:
    def _make_summary(self, **kwargs):
        defaults = dict(
            total_cost_usd=1.23,
            total_invocations=100,
            avg_cost_per_invocation_usd=0.0123,
            active_flow_count=5,
            date_range=DateRange(from_=date(2026, 1, 1), to=date(2026, 3, 1)),
        )
        defaults.update(kwargs)
        return UsageSummary(**defaults)

    def test_basic_fields(self):
        s = self._make_summary()
        assert s.total_cost_usd == 1.23
        assert s.total_invocations == 100
        assert s.avg_cost_per_invocation_usd == 0.0123
        assert s.active_flow_count == 5

    def test_defaults(self):
        s = self._make_summary()
        assert s.cached is False
        assert s.truncated is False
        assert s.currency == "USD"
        assert s.data_source == "langwatch"
        assert s.cache_age_seconds is None

    def test_cached_flag(self):
        s = self._make_summary(cached=True, cache_age_seconds=30)
        assert s.cached is True
        assert s.cache_age_seconds == 30

    def test_truncated_flag(self):
        s = self._make_summary(truncated=True)
        assert s.truncated is True


# ── FlowUsage ─────────────────────────────────────────────────────────────────

class TestFlowUsage:
    def test_all_fields(self):
        flow_id = uuid4()
        owner_id = uuid4()
        fu = FlowUsage(
            flow_id=flow_id,
            flow_name="My Flow",
            total_cost_usd=0.05,
            invocation_count=10,
            avg_cost_per_invocation_usd=0.005,
            owner_user_id=owner_id,
            owner_username="alice",
        )
        assert fu.flow_id == flow_id
        assert fu.flow_name == "My Flow"
        assert fu.total_cost_usd == 0.05
        assert fu.invocation_count == 10
        assert fu.avg_cost_per_invocation_usd == 0.005
        assert fu.owner_user_id == owner_id
        assert fu.owner_username == "alice"


# ── UsageResponse ─────────────────────────────────────────────────────────────

class TestUsageResponse:
    def _make_response(self):
        flow_id = uuid4()
        owner_id = uuid4()
        summary = UsageSummary(
            total_cost_usd=1.0,
            total_invocations=5,
            avg_cost_per_invocation_usd=0.2,
            active_flow_count=1,
            date_range=DateRange(from_=date(2026, 1, 1), to=date(2026, 3, 1)),
        )
        flow = FlowUsage(
            flow_id=flow_id,
            flow_name="Test Flow",
            total_cost_usd=1.0,
            invocation_count=5,
            avg_cost_per_invocation_usd=0.2,
            owner_user_id=owner_id,
            owner_username="bob",
        )
        return UsageResponse(summary=summary, flows=[flow])

    def test_round_trip_json(self):
        resp = self._make_response()
        json_str = resp.model_dump_json()
        restored = UsageResponse.model_validate_json(json_str)
        assert restored.summary.total_cost_usd == resp.summary.total_cost_usd
        assert restored.summary.total_invocations == resp.summary.total_invocations
        assert len(restored.flows) == len(resp.flows)
        assert restored.flows[0].flow_name == resp.flows[0].flow_name

    def test_json_serializable(self):
        resp = self._make_response()
        json_str = resp.model_dump_json()
        # Must be valid JSON
        data = json.loads(json_str)
        assert "summary" in data
        assert "flows" in data


# ── RunDetail ─────────────────────────────────────────────────────────────────

class TestRunDetail:
    def test_minimal(self):
        rd = RunDetail(
            run_id="run-001",
            started_at=datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
            cost_usd=0.01,
        )
        assert rd.run_id == "run-001"
        assert rd.status == "success"
        assert rd.input_tokens is None
        assert rd.output_tokens is None
        assert rd.total_tokens is None
        assert rd.model is None
        assert rd.duration_ms is None

    def test_all_fields(self):
        rd = RunDetail(
            run_id="run-002",
            started_at=datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
            cost_usd=0.05,
            input_tokens=100,
            output_tokens=200,
            total_tokens=300,
            model="gpt-4o",
            duration_ms=1500,
            status="error",
        )
        assert rd.input_tokens == 100
        assert rd.output_tokens == 200
        assert rd.total_tokens == 300
        assert rd.model == "gpt-4o"
        assert rd.duration_ms == 1500
        assert rd.status == "error"

    def test_status_literals(self):
        for status in ("success", "error", "partial"):
            rd = RunDetail(
                run_id="run-003",
                started_at=datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
                cost_usd=0.0,
                status=status,
            )
            assert rd.status == status

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            RunDetail(
                run_id="run-004",
                started_at=datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
                cost_usd=0.0,
                status="pending",
            )


# ── FlowRunsResponse ──────────────────────────────────────────────────────────

class TestFlowRunsResponse:
    def test_all_fields(self):
        flow_id = uuid4()
        rd = RunDetail(
            run_id="run-001",
            started_at=datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
            cost_usd=0.01,
        )
        resp = FlowRunsResponse(
            flow_id=flow_id,
            flow_name="My Flow",
            runs=[rd],
            total_runs_in_period=1,
        )
        assert resp.flow_id == flow_id
        assert resp.flow_name == "My Flow"
        assert len(resp.runs) == 1
        assert resp.total_runs_in_period == 1

    def test_empty_runs(self):
        resp = FlowRunsResponse(
            flow_id=uuid4(),
            flow_name="Empty Flow",
            runs=[],
            total_runs_in_period=0,
        )
        assert resp.runs == []
        assert resp.total_runs_in_period == 0


# ── SaveKeyResponse ───────────────────────────────────────────────────────────

class TestSaveKeyResponse:
    def test_all_fields(self):
        resp = SaveKeyResponse(
            success=True,
            key_preview="lw-****1234",
            message="API key saved successfully",
        )
        assert resp.success is True
        assert resp.key_preview == "lw-****1234"
        assert resp.message == "API key saved successfully"

    def test_failure(self):
        resp = SaveKeyResponse(
            success=False,
            key_preview="",
            message="Invalid key",
        )
        assert resp.success is False


# ── KeyStatusResponse ─────────────────────────────────────────────────────────

class TestKeyStatusResponse:
    def test_no_key(self):
        resp = KeyStatusResponse(has_key=False)
        assert resp.has_key is False
        assert resp.key_preview is None
        assert resp.configured_at is None

    def test_with_key(self):
        now = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
        resp = KeyStatusResponse(
            has_key=True,
            key_preview="lw-****5678",
            configured_at=now,
        )
        assert resp.has_key is True
        assert resp.key_preview == "lw-****5678"
        assert resp.configured_at == now
