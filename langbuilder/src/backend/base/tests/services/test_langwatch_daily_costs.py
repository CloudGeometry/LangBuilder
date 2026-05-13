"""Tests for DailyCost schema and date bucketing in _aggregate_with_metadata().

Covers Task 1 acceptance criteria for the cost-trend-chart feature.
TDD RED phase: these tests are written BEFORE the implementation.
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from langflow.services.langwatch.schemas import UsageQueryParams
from langflow.services.langwatch.service import LangWatchService


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def service():
    svc = LangWatchService.__new__(LangWatchService)
    svc._db_session = MagicMock()
    svc._client = LangWatchService._create_httpx_client()
    return svc


def _make_trace(flow_name: str, cost: float, started_at_ms: int | None) -> dict:
    """Build a minimal raw trace dict for testing."""
    trace: dict = {
        "trace_id": f"t_{started_at_ms}_{flow_name}",
        "metadata": {"labels": [f"Flow: {flow_name}"]},
        "metrics": {"total_cost": cost},
        "timestamps": {"started_at": started_at_ms},
        "spans": [{"type": "workflow", "name": flow_name}],
        "error": None,
    }
    return trace


# Epoch ms for specific dates (UTC midnight)
def _date_to_ms(d: date) -> int:
    """Convert a date to epoch milliseconds at UTC midnight."""
    from datetime import datetime, timezone

    dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


# ── Schema Tests ──────────────────────────────────────────────────────────────


class TestDailyCostSchema:
    """Test the DailyCost Pydantic model."""

    def test_daily_cost_exists(self):
        """DailyCost model can be imported from schemas."""
        from langflow.services.langwatch.schemas import DailyCost

        dc = DailyCost(date=date(2026, 3, 15), cost_usd=0.005, invocations=3)
        assert dc.date == date(2026, 3, 15)
        assert dc.cost_usd == 0.005
        assert dc.invocations == 3

    def test_daily_cost_serializes_date_as_iso_string(self):
        """DailyCost.date serializes as YYYY-MM-DD string in JSON."""
        import json

        from langflow.services.langwatch.schemas import DailyCost

        dc = DailyCost(date=date(2026, 3, 15), cost_usd=1.23, invocations=10)
        data = json.loads(dc.model_dump_json())
        assert data["date"] == "2026-03-15"

    def test_usage_response_has_daily_costs_field(self):
        """UsageResponse has daily_costs field with default empty list."""
        from langflow.services.langwatch.schemas import (
            DateRange,
            UsageResponse,
            UsageSummary,
        )

        resp = UsageResponse(
            summary=UsageSummary(
                total_cost_usd=0.0,
                total_invocations=0,
                avg_cost_per_invocation_usd=0.0,
                active_flow_count=0,
                date_range=DateRange(),
            ),
            flows=[],
        )
        assert resp.daily_costs == []

    def test_usage_response_without_daily_costs_kwarg(self):
        """UsageResponse can be constructed without daily_costs (default kicks in).

        CRITICAL: _empty_summary() in router.py constructs UsageResponse
        without daily_costs. This MUST NOT raise a validation error.
        """
        from langflow.services.langwatch.schemas import (
            DateRange,
            UsageResponse,
            UsageSummary,
        )

        # Simulates router.py _empty_summary()
        resp = UsageResponse(
            summary=UsageSummary(
                total_cost_usd=0.0,
                total_invocations=0,
                avg_cost_per_invocation_usd=0.0,
                active_flow_count=0,
                date_range=DateRange(from_=date(2026, 3, 1), to=date(2026, 3, 19)),
            ),
            flows=[],
        )
        assert hasattr(resp, "daily_costs")
        assert resp.daily_costs == []

    def test_usage_response_deserialization_without_daily_costs(self):
        """Cached JSON without daily_costs can be deserialized (default kicks in).

        Simulates reading a cached response written before the daily_costs
        field was added.
        """
        import json

        from langflow.services.langwatch.schemas import UsageResponse

        old_json = json.dumps(
            {
                "summary": {
                    "total_cost_usd": 1.0,
                    "total_invocations": 5,
                    "avg_cost_per_invocation_usd": 0.2,
                    "active_flow_count": 1,
                    "date_range": {"from": "2026-03-01", "to": "2026-03-19"},
                    "currency": "USD",
                    "data_source": "langwatch",
                    "cached": False,
                    "cache_age_seconds": None,
                    "truncated": False,
                },
                "flows": [],
            }
        )
        restored = UsageResponse.model_validate_json(old_json)
        assert restored.daily_costs == []


# ── Date Bucketing Tests ──────────────────────────────────────────────────────


class TestDailyBucketing:
    """Test daily cost bucketing in _aggregate_with_metadata()."""

    def test_daily_costs_present_in_response(self, service):
        """_aggregate_with_metadata returns daily_costs in the response."""
        params = UsageQueryParams(
            from_date=date(2026, 3, 15),
            to_date=date(2026, 3, 19),
        )
        traces = [_make_trace("Bot", 0.01, _date_to_ms(date(2026, 3, 16)))]
        result = service._aggregate_with_metadata(traces, params)
        assert hasattr(result, "daily_costs")
        assert isinstance(result.daily_costs, list)

    def test_daily_costs_length_matches_date_range(self, service):
        """daily_costs has one entry per day in the date range (inclusive)."""
        params = UsageQueryParams(
            from_date=date(2026, 3, 15),
            to_date=date(2026, 3, 19),
        )
        traces = [_make_trace("Bot", 0.01, _date_to_ms(date(2026, 3, 16)))]
        result = service._aggregate_with_metadata(traces, params)
        assert len(result.daily_costs) == 5  # 15, 16, 17, 18, 19

    def test_daily_costs_sorted_ascending(self, service):
        """daily_costs is sorted by date ascending."""
        params = UsageQueryParams(
            from_date=date(2026, 3, 15),
            to_date=date(2026, 3, 19),
        )
        traces = [
            _make_trace("Bot", 0.02, _date_to_ms(date(2026, 3, 18))),
            _make_trace("Bot", 0.01, _date_to_ms(date(2026, 3, 15))),
        ]
        result = service._aggregate_with_metadata(traces, params)
        dates = [dc.date for dc in result.daily_costs]
        assert dates == sorted(dates)

    def test_gap_filling_with_zeros(self, service):
        """Days without traces are filled with cost_usd=0.0, invocations=0."""
        params = UsageQueryParams(
            from_date=date(2026, 3, 15),
            to_date=date(2026, 3, 19),
        )
        # Only one trace on March 16
        traces = [_make_trace("Bot", 0.05, _date_to_ms(date(2026, 3, 16)))]
        result = service._aggregate_with_metadata(traces, params)

        assert len(result.daily_costs) == 5
        # March 15 should be zero-filled
        day_15 = next(dc for dc in result.daily_costs if dc.date == date(2026, 3, 15))
        assert day_15.cost_usd == 0.0
        assert day_15.invocations == 0

        # March 16 should have the trace data
        day_16 = next(dc for dc in result.daily_costs if dc.date == date(2026, 3, 16))
        assert day_16.cost_usd == 0.05
        assert day_16.invocations == 1

    def test_multiple_traces_same_day(self, service):
        """Multiple traces on the same day are summed."""
        params = UsageQueryParams(
            from_date=date(2026, 3, 15),
            to_date=date(2026, 3, 15),
        )
        traces = [
            _make_trace("Bot A", 0.01, _date_to_ms(date(2026, 3, 15))),
            _make_trace("Bot B", 0.02, _date_to_ms(date(2026, 3, 15))),
            _make_trace("Bot A", 0.03, _date_to_ms(date(2026, 3, 15))),
        ]
        result = service._aggregate_with_metadata(traces, params)
        assert len(result.daily_costs) == 1
        assert result.daily_costs[0].date == date(2026, 3, 15)
        assert abs(result.daily_costs[0].cost_usd - 0.06) < 1e-9
        assert result.daily_costs[0].invocations == 3

    def test_single_day_range(self, service):
        """from_date == to_date produces exactly 1 entry."""
        params = UsageQueryParams(
            from_date=date(2026, 3, 15),
            to_date=date(2026, 3, 15),
        )
        traces = [_make_trace("Bot", 0.01, _date_to_ms(date(2026, 3, 15)))]
        result = service._aggregate_with_metadata(traces, params)
        assert len(result.daily_costs) == 1

    def test_zero_cost_trace_increments_invocations(self, service):
        """Zero-cost traces still count as invocations."""
        params = UsageQueryParams(
            from_date=date(2026, 3, 15),
            to_date=date(2026, 3, 15),
        )
        traces = [_make_trace("Bot", 0.0, _date_to_ms(date(2026, 3, 15)))]
        result = service._aggregate_with_metadata(traces, params)
        assert result.daily_costs[0].invocations == 1
        assert result.daily_costs[0].cost_usd == 0.0


class TestDailyBucketingEdgeCases:
    """Edge case tests for daily cost bucketing."""

    def test_no_traces_with_explicit_dates(self, service):
        """No traces in range with explicit dates -> zero-cost entries covering the range."""
        params = UsageQueryParams(
            from_date=date(2026, 3, 15),
            to_date=date(2026, 3, 17),
        )
        result = service._aggregate_with_metadata([], params)
        assert len(result.daily_costs) == 3
        for dc in result.daily_costs:
            assert dc.cost_usd == 0.0
            assert dc.invocations == 0

    def test_no_traces_no_dates(self, service):
        """No traces, both dates None -> daily_costs is []."""
        params = UsageQueryParams(from_date=None, to_date=None)
        result = service._aggregate_with_metadata([], params)
        assert result.daily_costs == []

    def test_inverted_date_range(self, service):
        """from_date > to_date -> daily_costs is []."""
        params = UsageQueryParams(
            from_date=date(2026, 3, 20),
            to_date=date(2026, 3, 15),
        )
        traces = [_make_trace("Bot", 0.01, _date_to_ms(date(2026, 3, 17)))]
        result = service._aggregate_with_metadata(traces, params)
        assert result.daily_costs == []

    def test_started_at_ms_null_skipped(self, service):
        """Traces with started_at_ms=None are skipped in bucketing (not erroring)."""
        params = UsageQueryParams(
            from_date=date(2026, 3, 15),
            to_date=date(2026, 3, 16),
        )
        traces = [
            _make_trace("Bot", 0.01, None),  # null timestamp
            _make_trace("Bot", 0.02, _date_to_ms(date(2026, 3, 15))),
        ]
        result = service._aggregate_with_metadata(traces, params)
        # The null-timestamp trace is skipped in daily bucketing
        assert len(result.daily_costs) == 2
        day_15 = next(dc for dc in result.daily_costs if dc.date == date(2026, 3, 15))
        assert day_15.invocations == 1  # only the non-null trace
        assert day_15.cost_usd == 0.02

    def test_epoch_zero_trace_bucketed_but_capped(self, service):
        """Trace with started_at_ms=0 (epoch zero, 1970) is bucketed normally.

        Gap filling uses capped range (max 366 days), not from 1970.
        """
        params = UsageQueryParams(
            from_date=date(2026, 3, 15),
            to_date=date(2026, 3, 17),
        )
        traces = [
            _make_trace("Bot", 0.01, 0),  # epoch zero = 1970-01-01
            _make_trace("Bot", 0.02, _date_to_ms(date(2026, 3, 16))),
        ]
        result = service._aggregate_with_metadata(traces, params)
        # Gap filling should cover from_date to to_date (3 days), NOT from 1970
        assert len(result.daily_costs) == 3
        # The epoch zero trace is outside the date range so its cost shouldn't
        # appear in any of these buckets
        day_16 = next(dc for dc in result.daily_costs if dc.date == date(2026, 3, 16))
        assert day_16.cost_usd == 0.02

    def test_flow_name_none_excluded_from_daily_costs(self, service):
        """Traces with flow_name=None are excluded from daily_costs.

        Consistent with being excluded from flows.
        """
        params = UsageQueryParams(
            from_date=date(2026, 3, 15),
            to_date=date(2026, 3, 15),
        )
        # Trace with no flow label
        trace_no_flow: dict = {
            "trace_id": "t_no_flow",
            "metadata": {"labels": []},
            "metrics": {"total_cost": 9.99},
            "timestamps": {"started_at": _date_to_ms(date(2026, 3, 15))},
            "spans": [],
            "error": None,
        }
        traces = [
            trace_no_flow,
            _make_trace("Bot", 0.01, _date_to_ms(date(2026, 3, 15))),
        ]
        result = service._aggregate_with_metadata(traces, params)
        assert result.daily_costs[0].invocations == 1  # only the "Bot" trace
        assert result.daily_costs[0].cost_usd == 0.01  # not 10.00

    def test_gap_fill_capped_at_366_days(self, service):
        """Gap filling is capped at 366 days maximum."""
        params = UsageQueryParams(
            from_date=date(2024, 1, 1),
            to_date=date(2026, 3, 19),
        )
        traces = [_make_trace("Bot", 0.01, _date_to_ms(date(2026, 3, 15)))]
        result = service._aggregate_with_metadata(traces, params)
        assert len(result.daily_costs) <= 366

    def test_both_dates_none_with_traces(self, service):
        """Both dates None with traces -> gap-fill between min and max trace dates."""
        params = UsageQueryParams(from_date=None, to_date=None)
        traces = [
            _make_trace("Bot", 0.01, _date_to_ms(date(2026, 3, 10))),
            _make_trace("Bot", 0.02, _date_to_ms(date(2026, 3, 13))),
        ]
        result = service._aggregate_with_metadata(traces, params)
        # Should fill 10, 11, 12, 13 = 4 days
        assert len(result.daily_costs) == 4
        assert result.daily_costs[0].date == date(2026, 3, 10)
        assert result.daily_costs[-1].date == date(2026, 3, 13)

    def test_summary_and_flows_unchanged(self, service):
        """Existing summary and flows fields are unchanged after adding daily_costs."""
        params = UsageQueryParams(
            from_date=date(2026, 3, 15),
            to_date=date(2026, 3, 19),
        )
        traces = [
            _make_trace("Bot A", 0.01, _date_to_ms(date(2026, 3, 15))),
            _make_trace("Bot A", 0.02, _date_to_ms(date(2026, 3, 16))),
            _make_trace("Bot B", 0.05, _date_to_ms(date(2026, 3, 17))),
        ]
        result = service._aggregate_with_metadata(traces, params)

        # Summary totals
        assert result.summary.total_invocations == 3
        assert abs(result.summary.total_cost_usd - 0.08) < 1e-6
        assert result.summary.active_flow_count == 2

        # Flows
        assert len(result.flows) == 2
        flow_names = {f.flow_name for f in result.flows}
        assert flow_names == {"Bot A", "Bot B"}

        # daily_costs is present and correct
        assert len(result.daily_costs) == 5
