import type {
  FlowRunsQueryParams,
  FlowRunsResponse,
  FlowUsage,
  KeyStatusResponse,
  RunDetail,
  UsageQueryParams,
  UsageResponse,
  UsageSummary,
} from "@/types/usage";

describe("Usage TypeScript Types", () => {
  describe("UsageQueryParams", () => {
    it("accepts all optional fields", () => {
      const params: UsageQueryParams = {
        from_date: "2025-01-01",
        to_date: "2025-12-31",
        user_id: "user-123",
        sub_view: "flows",
      };
      expect(params.from_date).toBe("2025-01-01");
      expect(params.sub_view).toBe("flows");
    });

    it("accepts empty object", () => {
      const params: UsageQueryParams = {};
      expect(params).toBeDefined();
    });

    it("accepts null values for date fields", () => {
      const params: UsageQueryParams = {
        from_date: null,
        to_date: null,
        user_id: null,
      };
      expect(params.from_date).toBeNull();
    });
  });

  describe("FlowRunsQueryParams", () => {
    it("accepts all optional fields", () => {
      const params: FlowRunsQueryParams = {
        from_date: "2025-01-01",
        to_date: "2025-12-31",
        limit: 50,
      };
      expect(params.limit).toBe(50);
    });
  });

  describe("UsageSummary", () => {
    it("has all required fields", () => {
      const summary: UsageSummary = {
        total_cost_usd: 1.5,
        total_invocations: 100,
        avg_cost_per_invocation_usd: 0.015,
        active_flow_count: 5,
        date_range: { from: null, to: null },
        currency: "USD",
        data_source: "langwatch",
        cached: false,
        cache_age_seconds: null,
        truncated: false,
      };
      expect(summary.total_cost_usd).toBe(1.5);
      expect(summary.total_invocations).toBe(100);
      expect(summary.active_flow_count).toBe(5);
    });

    it("supports date_range with from/to", () => {
      const summary: UsageSummary = {
        total_cost_usd: 0,
        total_invocations: 0,
        avg_cost_per_invocation_usd: 0,
        active_flow_count: 0,
        date_range: { from: "2025-01-01", to: "2025-12-31" },
        currency: "USD",
        data_source: "langwatch",
        cached: true,
        cache_age_seconds: 120,
        truncated: false,
      };
      expect(summary.date_range.from).toBe("2025-01-01");
      expect(summary.date_range.to).toBe("2025-12-31");
    });
  });

  describe("FlowUsage", () => {
    it("has all required fields", () => {
      const flow: FlowUsage = {
        flow_id: "flow-1",
        flow_name: "Test Flow",
        total_cost_usd: 0.5,
        invocation_count: 50,
        avg_cost_per_invocation_usd: 0.01,
        owner_user_id: "user-1",
        owner_username: "testuser",
      };
      expect(flow.flow_id).toBe("flow-1");
      expect(flow.invocation_count).toBe(50);
    });
  });

  describe("UsageResponse", () => {
    it("has summary and flows fields", () => {
      const response: UsageResponse = {
        summary: {
          total_cost_usd: 1.0,
          total_invocations: 10,
          avg_cost_per_invocation_usd: 0.1,
          active_flow_count: 1,
          date_range: { from: null, to: null },
          currency: "USD",
          data_source: "langwatch",
          cached: false,
          cache_age_seconds: null,
          truncated: false,
        },
        flows: [],
      };
      expect(response.flows).toEqual([]);
      expect(response.summary.total_invocations).toBe(10);
    });
  });

  describe("RunDetail", () => {
    it("has required fields with status union type", () => {
      const run: RunDetail = {
        run_id: "run-1",
        started_at: "2025-01-01T00:00:00Z",
        cost_usd: 0.01,
        status: "success",
      };
      expect(run.status).toBe("success");
    });

    it("accepts all status values", () => {
      const successRun: RunDetail = { run_id: "r1", started_at: "2025-01-01T00:00:00Z", cost_usd: 0, status: "success" };
      const errorRun: RunDetail = { run_id: "r2", started_at: "2025-01-01T00:00:00Z", cost_usd: 0, status: "error" };
      const partialRun: RunDetail = { run_id: "r3", started_at: "2025-01-01T00:00:00Z", cost_usd: 0, status: "partial" };
      expect(successRun.status).toBe("success");
      expect(errorRun.status).toBe("error");
      expect(partialRun.status).toBe("partial");
    });

    it("accepts optional fields", () => {
      const run: RunDetail = {
        run_id: "run-1",
        started_at: "2025-01-01T00:00:00Z",
        cost_usd: 0.01,
        status: "success",
        input_tokens: 100,
        output_tokens: 200,
        total_tokens: 300,
        model: "gpt-4",
        duration_ms: 1500,
      };
      expect(run.model).toBe("gpt-4");
      expect(run.total_tokens).toBe(300);
    });
  });

  describe("FlowRunsResponse", () => {
    it("has all required fields", () => {
      const response: FlowRunsResponse = {
        flow_id: "flow-1",
        flow_name: "Test Flow",
        runs: [],
        total_runs_in_period: 0,
      };
      expect(response.flow_id).toBe("flow-1");
      expect(response.runs).toEqual([]);
    });
  });

  describe("KeyStatusResponse", () => {
    it("has all required fields", () => {
      const status: KeyStatusResponse = {
        has_key: true,
        key_preview: "lw_****1234",
        configured_at: "2025-01-01T00:00:00Z",
      };
      expect(status.has_key).toBe(true);
    });

    it("accepts null values for optional fields", () => {
      const status: KeyStatusResponse = {
        has_key: false,
        key_preview: null,
        configured_at: null,
      };
      expect(status.has_key).toBe(false);
      expect(status.key_preview).toBeNull();
    });
  });
});
