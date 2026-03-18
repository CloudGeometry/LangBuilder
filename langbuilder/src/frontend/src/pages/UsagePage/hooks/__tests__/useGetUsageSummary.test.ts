import { useGetUsageSummary } from "../useGetUsageSummary";

// Mock the service
jest.mock("@/services/LangWatchService", () => ({
  getUsageSummary: jest.fn(),
}));

// Mock @tanstack/react-query
const mockUseQuery = jest.fn();
jest.mock("@tanstack/react-query", () => ({
  useQuery: (options: unknown) => mockUseQuery(options),
  keepPreviousData: "keepPreviousData",
}));

describe("useGetUsageSummary", () => {
  beforeEach(() => {
    mockUseQuery.mockReset();
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: true });
  });

  it("calls useQuery with correct queryKey", () => {
    const params = { from_date: "2025-01-01", to_date: "2025-12-31" };
    useGetUsageSummary(params);

    expect(mockUseQuery).toHaveBeenCalledTimes(1);
    const options = mockUseQuery.mock.calls[0][0];
    expect(options.queryKey).toEqual(["usage", "summary", params]);
  });

  it("configures staleTime to 4 minutes", () => {
    useGetUsageSummary({});

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.staleTime).toBe(4 * 60 * 1000);
  });

  it("configures gcTime to 10 minutes", () => {
    useGetUsageSummary({});

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.gcTime).toBe(10 * 60 * 1000);
  });

  it("configures retry to 2", () => {
    useGetUsageSummary({});

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.retry).toBe(2);
  });

  it("uses keepPreviousData for placeholderData", () => {
    useGetUsageSummary({});

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.placeholderData).toBe("keepPreviousData");
  });

  it("configures retryDelay with exponential backoff capped at 5000ms", () => {
    useGetUsageSummary({});

    const options = mockUseQuery.mock.calls[0][0];
    expect(options.retryDelay(0)).toBe(1000);
    expect(options.retryDelay(1)).toBe(2000);
    expect(options.retryDelay(2)).toBe(4000);
    expect(options.retryDelay(10)).toBe(5000); // capped
  });
});
