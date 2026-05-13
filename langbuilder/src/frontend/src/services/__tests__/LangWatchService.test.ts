import {
  getFlowRuns,
  getKeyStatus,
  getUsageSummary,
  saveLangWatchKey,
} from "@/services/LangWatchService";

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

describe("LangWatchService", () => {
  describe("imports", () => {
    it("exports getUsageSummary function", () => {
      expect(typeof getUsageSummary).toBe("function");
    });

    it("exports getFlowRuns function", () => {
      expect(typeof getFlowRuns).toBe("function");
    });

    it("exports getKeyStatus function", () => {
      expect(typeof getKeyStatus).toBe("function");
    });

    it("exports saveLangWatchKey function", () => {
      expect(typeof saveLangWatchKey).toBe("function");
    });
  });

  describe("getUsageSummary", () => {
    it("calls correct URL for /api/v1/usage/", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ summary: {}, flows: [] }),
      });

      await getUsageSummary({});

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain("usage/");
    });

    it("appends from_date query param when provided", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ summary: {}, flows: [] }),
      });

      await getUsageSummary({ from_date: "2025-01-01" });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain("from_date=2025-01-01");
    });

    it("appends to_date query param when provided", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ summary: {}, flows: [] }),
      });

      await getUsageSummary({ to_date: "2025-12-31" });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain("to_date=2025-12-31");
    });

    it("appends user_id query param when provided", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ summary: {}, flows: [] }),
      });

      await getUsageSummary({ user_id: "user-123" });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain("user_id=user-123");
    });

    it("throws an Error instance when response is not ok", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Unauthorized" }),
        statusText: "Unauthorized",
      });

      await expect(getUsageSummary({})).rejects.toThrow("Unauthorized");
    });

    it("thrown error is an Error instance", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Unauthorized" }),
        statusText: "Unauthorized",
      });

      await expect(getUsageSummary({})).rejects.toBeInstanceOf(Error);
    });

    it("does not append null params", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ summary: {}, flows: [] }),
      });

      await getUsageSummary({ from_date: null, to_date: null });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).not.toContain("from_date");
      expect(calledUrl).not.toContain("to_date");
    });
  });

  describe("getFlowRuns", () => {
    it("calls correct URL with flowId", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ flow_id: "flow-1", flow_name: "Flow", runs: [], total_runs_in_period: 0 }),
      });

      await getFlowRuns("flow-1", {});

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain("usage/flow-1/runs");
    });

    it("appends limit param when provided", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ flow_id: "flow-1", flow_name: "Flow", runs: [], total_runs_in_period: 0 }),
      });

      await getFlowRuns("flow-1", { limit: 10 });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain("limit=10");
    });

    it("throws an Error instance when response is not ok", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Not found" }),
        statusText: "Not Found",
      });

      await expect(getFlowRuns("flow-1", {})).rejects.toThrow("Not found");
    });

    it("thrown error is an Error instance", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Not found" }),
        statusText: "Not Found",
      });

      await expect(getFlowRuns("flow-1", {})).rejects.toBeInstanceOf(Error);
    });
  });

  describe("getKeyStatus", () => {
    it("calls correct URL for key status", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ has_key: true, key_preview: "lw_****", configured_at: null }),
      });

      await getKeyStatus();

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain("usage/settings/langwatch-key/status");
    });

    it("returns key status response", async () => {
      const mockResponse = { has_key: false, key_preview: null, configured_at: null };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await getKeyStatus();

      expect(result).toEqual(mockResponse);
    });
  });

  describe("saveLangWatchKey", () => {
    it("calls correct URL with POST method", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await saveLangWatchKey("test-api-key");

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain("usage/settings/langwatch-key");
      const options = mockFetch.mock.calls[0][1];
      expect(options.method).toBe("POST");
    });

    it("sends api_key in request body", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await saveLangWatchKey("my-api-key");

      const options = mockFetch.mock.calls[0][1];
      const body = JSON.parse(options.body);
      expect(body.api_key).toBe("my-api-key");
    });
  });
});
