import { render, screen } from "@testing-library/react";
import { UsagePage } from "../UsagePage";

// Mock the hooks
const mockUseGetUsageSummary = jest.fn();
jest.mock("../hooks/useGetUsageSummary", () => ({
  useGetUsageSummary: () => mockUseGetUsageSummary(),
}));

// Mock useDebounce to return value immediately
jest.mock("@/hooks/useDebounce", () => ({
  useDebounce: (value: unknown) => value,
}));

// Mock child components
jest.mock("../components/LoadingSkeleton", () => ({
  UsageLoadingSkeleton: () => (
    <div data-testid="usage-loading-skeleton">Loading...</div>
  ),
}));

jest.mock("../components/UsageSummaryCards", () => ({
  UsageSummaryCards: ({ summary }: { summary: { total_invocations: number } }) => (
    <div data-testid="usage-summary-cards">
      {summary.total_invocations}
    </div>
  ),
}));

jest.mock("../components/DateRangePicker", () => ({
  DateRangePicker: () => <div data-testid="date-range-picker" />,
}));

jest.mock("../components/UserFilterDropdown", () => ({
  UserFilterDropdown: () => <div data-testid="user-filter-dropdown" />,
}));

describe("UsagePage", () => {
  beforeEach(() => {
    mockUseGetUsageSummary.mockReset();
  });

  it("shows loading skeleton when loading and no data", () => {
    mockUseGetUsageSummary.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    });

    render(<UsagePage />);

    expect(screen.getByTestId("usage-loading-skeleton")).toBeInTheDocument();
  });

  it("shows error state when error occurs", () => {
    mockUseGetUsageSummary.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("API Error"),
    });

    render(<UsagePage />);

    expect(screen.getByTestId("usage-error-state")).toBeInTheDocument();
    expect(screen.getByText("Failed to load usage data")).toBeInTheDocument();
  });

  it("shows empty state when no data and not loading", () => {
    mockUseGetUsageSummary.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
    });

    render(<UsagePage />);

    expect(screen.getByTestId("usage-empty-state")).toBeInTheDocument();
  });

  it("shows dashboard when data is available", () => {
    const mockData = {
      summary: {
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
      },
      flows: [],
    };

    mockUseGetUsageSummary.mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
      error: null,
    });

    render(<UsagePage />);

    expect(screen.getByTestId("usage-dashboard")).toBeInTheDocument();
    expect(screen.getByTestId("usage-summary-cards")).toBeInTheDocument();
    expect(screen.getByTestId("date-range-picker")).toBeInTheDocument();
    expect(screen.getByTestId("user-filter-dropdown")).toBeInTheDocument();
  });

  it("does not show skeleton when data is available even if loading", () => {
    const mockData = {
      summary: {
        total_cost_usd: 0,
        total_invocations: 0,
        avg_cost_per_invocation_usd: 0,
        active_flow_count: 0,
        date_range: { from: null, to: null },
        currency: "USD",
        data_source: "langwatch",
        cached: false,
        cache_age_seconds: null,
        truncated: false,
      },
      flows: [],
    };

    mockUseGetUsageSummary.mockReturnValue({
      data: mockData,
      isLoading: true,
      isError: false,
      error: null,
    });

    render(<UsagePage />);

    expect(screen.queryByTestId("usage-loading-skeleton")).not.toBeInTheDocument();
    expect(screen.getByTestId("usage-dashboard")).toBeInTheDocument();
  });
});
