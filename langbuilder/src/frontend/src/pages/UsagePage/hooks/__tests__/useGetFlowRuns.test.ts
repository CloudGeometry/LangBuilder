import { useGetFlowRuns } from "../useGetFlowRuns";

// Mock the service
jest.mock("@/services/LangWatchService", () => ({
  getFlowRuns: jest.fn(),
}));

// Mock @tanstack/react-query
const mockUseQuery = jest.fn();
jest.mock("@tanstack/react-query", () => ({
  useQuery: (options: unknown) => mockUseQuery(options),
}));

describe("useGetFlowRuns", () => {
  beforeEach(() => {
    mockUseQuery.mockReset();
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: false });
  });

  it("calls useQuery with correct queryKey including flowId", () => {
    const params = { from_date: "2025-01-01" };
    useGetFlowRuns("flow-1", params);

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.queryKey).toEqual(["usage", "flow-runs", "flow-1", params]);
  });

  it("is enabled when flowId is provided", () => {
    useGetFlowRuns("flow-1", {});

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.enabled).toBe(true);
  });

  it("is disabled when flowId is null", () => {
    useGetFlowRuns(null, {});

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.enabled).toBe(false);
  });

  it("configures staleTime to 4 minutes", () => {
    useGetFlowRuns("flow-1", {});

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.staleTime).toBe(4 * 60 * 1000);
  });

  it("configures retry to 2", () => {
    useGetFlowRuns("flow-1", {});

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.retry).toBe(2);
  });

  it("configures retryDelay with exponential backoff", () => {
    useGetFlowRuns("flow-1", {});

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.retryDelay(0)).toBe(1000);
    expect(options.retryDelay(1)).toBe(2000);
    expect(options.retryDelay(10)).toBe(5000); // capped
  });
});
