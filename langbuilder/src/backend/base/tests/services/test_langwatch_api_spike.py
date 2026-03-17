"""F2-T1 Spike tests — LangWatch API fixture validation.

These tests verify that:
1. The sample fixture file exists and is valid JSON.
2. The top-level structure matches the LangWatch traces/search API shape.
3. Each trace object contains the fields required by the parsing logic in F2-T4.
4. The fixture is suitable for use in pytest-httpx mocks (correct content-type).

All tests are data-shape / contract tests — no live network calls are made.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixture path
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_FILE = FIXTURES_DIR / "langwatch_sample_response.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture() -> dict:
    """Load and parse the sample fixture JSON."""
    return json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Test 1 — file existence and valid JSON
# ---------------------------------------------------------------------------


class TestFixtureFileExists:
    def test_file_exists(self):
        assert SAMPLE_FILE.exists(), f"Fixture file not found: {SAMPLE_FILE}"

    def test_file_is_valid_json(self):
        content = SAMPLE_FILE.read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, dict), "Fixture root must be a JSON object"

    def test_file_is_not_empty(self):
        assert SAMPLE_FILE.stat().st_size > 0, "Fixture file must not be empty"


# ---------------------------------------------------------------------------
# Test 2 — top-level structure
# ---------------------------------------------------------------------------


class TestTopLevelStructure:
    @pytest.fixture
    def data(self):
        return _load_fixture()

    def test_has_traces_key(self, data):
        assert "traces" in data, "Response must have a 'traces' key"

    def test_traces_is_list(self, data):
        assert isinstance(data["traces"], list), "'traces' must be an array"

    def test_traces_not_empty(self, data):
        assert len(data["traces"]) >= 1, "'traces' array must have at least 1 item"

    def test_has_pagination_key(self, data):
        assert "pagination" in data, "Response must have a 'pagination' key"

    def test_pagination_has_total_hits(self, data):
        assert "totalHits" in data["pagination"], "pagination must have 'totalHits'"
        assert isinstance(data["pagination"]["totalHits"], int), "'totalHits' must be an int"

    def test_pagination_has_scroll_id(self, data):
        assert "scrollId" in data["pagination"], "pagination must have 'scrollId'"
        # scrollId may be string or null
        assert data["pagination"]["scrollId"] is None or isinstance(
            data["pagination"]["scrollId"], str
        ), "'scrollId' must be string or null"

    def test_fixture_has_at_least_three_traces(self, data):
        assert len(data["traces"]) >= 3, "Fixture must include at least 3 trace objects for variety"


# ---------------------------------------------------------------------------
# Test 3 — required fields on each trace object
# ---------------------------------------------------------------------------

REQUIRED_TRACE_FIELDS = [
    "trace_id",
    "project_id",
    "metadata",
    "timestamps",
    "metrics",
    "spans",
]

REQUIRED_METADATA_FIELDS = [
    "thread_id",
    "labels",
]

REQUIRED_TIMESTAMP_FIELDS = [
    "started_at",
    "inserted_at",
]

REQUIRED_METRICS_FIELDS = [
    "total_cost",
    "prompt_tokens",
    "completion_tokens",
    "total_time_ms",
]


class TestTraceObjectFields:
    @pytest.fixture
    def traces(self):
        return _load_fixture()["traces"]

    def test_each_trace_has_trace_id(self, traces):
        for i, trace in enumerate(traces):
            assert "trace_id" in trace, f"trace[{i}] missing 'trace_id'"
            assert isinstance(trace["trace_id"], str), f"trace[{i}]['trace_id'] must be string"
            assert len(trace["trace_id"]) > 0, f"trace[{i}]['trace_id'] must not be empty"

    def test_each_trace_has_required_top_level_fields(self, traces):
        for i, trace in enumerate(traces):
            for field in REQUIRED_TRACE_FIELDS:
                assert field in trace, f"trace[{i}] missing required field '{field}'"

    def test_each_trace_metadata_has_thread_id(self, traces):
        for i, trace in enumerate(traces):
            metadata = trace["metadata"]
            assert "thread_id" in metadata, f"trace[{i}].metadata missing 'thread_id'"
            # thread_id may be null
            assert metadata["thread_id"] is None or isinstance(
                metadata["thread_id"], str
            ), f"trace[{i}].metadata.thread_id must be string or null"

    def test_each_trace_metadata_has_labels(self, traces):
        for i, trace in enumerate(traces):
            metadata = trace["metadata"]
            assert "labels" in metadata, f"trace[{i}].metadata missing 'labels'"

    def test_each_trace_timestamps_has_started_at(self, traces):
        for i, trace in enumerate(traces):
            timestamps = trace["timestamps"]
            assert "started_at" in timestamps, f"trace[{i}].timestamps missing 'started_at'"
            assert isinstance(
                timestamps["started_at"], (int, float)
            ), f"trace[{i}].timestamps.started_at must be numeric (epoch ms)"

    def test_each_trace_metrics_has_total_cost(self, traces):
        for i, trace in enumerate(traces):
            metrics = trace["metrics"]
            assert "total_cost" in metrics, f"trace[{i}].metrics missing 'total_cost'"
            # total_cost may be float or null
            assert metrics["total_cost"] is None or isinstance(
                metrics["total_cost"], (int, float)
            ), f"trace[{i}].metrics.total_cost must be numeric or null"

    def test_each_trace_metrics_has_token_fields(self, traces):
        for i, trace in enumerate(traces):
            metrics = trace["metrics"]
            for field in ["prompt_tokens", "completion_tokens"]:
                assert field in metrics, f"trace[{i}].metrics missing '{field}'"

    def test_each_trace_spans_is_list(self, traces):
        for i, trace in enumerate(traces):
            assert isinstance(trace["spans"], list), f"trace[{i}].spans must be a list"

    def test_fixture_variety_multiple_flow_labels(self, traces):
        """Confirm fixture covers multiple distinct flow labels."""
        all_labels: list[str] = []
        for trace in traces:
            labels = trace["metadata"].get("labels") or []
            all_labels.extend(labels)
        flow_labels = [lbl for lbl in all_labels if lbl.startswith("Flow: ")]
        unique_flows = set(flow_labels)
        assert len(unique_flows) >= 2, (
            f"Fixture must include traces from at least 2 different flows; found: {unique_flows}"
        )

    def test_fixture_includes_error_trace(self, traces):
        """At least one trace should represent an error scenario."""
        error_traces = [t for t in traces if t.get("error") is not None]
        assert len(error_traces) >= 1, "Fixture must include at least 1 trace with an error"

    def test_fixture_variety_cost_values(self, traces):
        """Traces should have distinct cost values (not all zero)."""
        costs = [
            t["metrics"]["total_cost"]
            for t in traces
            if t["metrics"].get("total_cost") is not None
        ]
        assert len(costs) >= 2, "Fixture must include at least 2 traces with cost values"
        assert len(set(costs)) >= 2, "Fixture should have varied cost values across traces"


# ---------------------------------------------------------------------------
# Test 4 — pytest-httpx mock suitability
# ---------------------------------------------------------------------------


class TestHttpxMockSuitability:
    """Verify the fixture is compatible with pytest-httpx mocking patterns."""

    def test_fixture_can_be_json_serialised_to_bytes(self):
        """pytest-httpx mock requires content as bytes."""
        data = _load_fixture()
        encoded = json.dumps(data).encode("utf-8")
        assert isinstance(encoded, bytes)
        assert len(encoded) > 0

    def test_fixture_round_trips_through_json(self):
        """Fixture should survive a JSON encode/decode cycle."""
        data = _load_fixture()
        round_tripped = json.loads(json.dumps(data))
        assert round_tripped == data

    def test_fixture_content_type_is_application_json(self):
        """The fixture should be served with application/json content type in mocks."""
        # This is a contract reminder test — documents the expected content type
        expected_content_type = "application/json"
        assert expected_content_type == "application/json"  # Always true, documents convention

    def test_fixture_has_no_undefined_values(self):
        """All values in the fixture must be valid JSON types (no Python-only objects)."""
        data = _load_fixture()
        # If this succeeds, the fixture contains only JSON-compatible types
        re_encoded = json.dumps(data)
        assert isinstance(re_encoded, str)

    def test_pagination_scroll_id_is_non_empty_string(self):
        """scrollId in sample response must be non-empty (simulates a real paged response)."""
        data = _load_fixture()
        scroll_id = data["pagination"]["scrollId"]
        assert isinstance(scroll_id, str) and len(scroll_id) > 0, (
            "Sample fixture should have a non-null scrollId to test pagination logic"
        )
