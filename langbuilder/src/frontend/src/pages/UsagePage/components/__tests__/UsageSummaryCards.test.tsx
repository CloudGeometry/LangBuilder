import { render, screen } from "@testing-library/react";
import { UsageSummaryCards } from "../UsageSummaryCards";
import type { UsageSummary } from "@/types/usage";

const mockSummary: UsageSummary = {
  total_cost_usd: 1.23456789,
  total_invocations: 1500,
  avg_cost_per_invocation_usd: 0.00082304526,
  active_flow_count: 7,
  date_range: { from: null, to: null },
  currency: "USD",
  data_source: "langwatch",
  cached: false,
  cache_age_seconds: null,
  truncated: false,
};

describe("UsageSummaryCards", () => {
  it("renders all 4 metric cards", () => {
    render(<UsageSummaryCards summary={mockSummary} />);

    expect(screen.getByTestId("summary-card-total-cost")).toBeInTheDocument();
    expect(screen.getByTestId("summary-card-total-invocations")).toBeInTheDocument();
    expect(screen.getByTestId("summary-card-avg-cost")).toBeInTheDocument();
    expect(screen.getByTestId("summary-card-active-flows")).toBeInTheDocument();
  });

  it("formats total cost to 4 decimal places", () => {
    render(<UsageSummaryCards summary={mockSummary} />);

    expect(screen.getByText("$1.2346")).toBeInTheDocument();
  });

  it("displays total invocations as integer", () => {
    render(<UsageSummaryCards summary={mockSummary} />);

    expect(screen.getByText("1,500")).toBeInTheDocument();
  });

  it("formats avg cost per invocation to 4 decimal places", () => {
    render(<UsageSummaryCards summary={mockSummary} />);

    expect(screen.getByText("$0.0008")).toBeInTheDocument();
  });

  it("displays active flow count as integer", () => {
    render(<UsageSummaryCards summary={mockSummary} />);

    expect(screen.getByText("7")).toBeInTheDocument();
  });

  it("renders labels for all cards", () => {
    render(<UsageSummaryCards summary={mockSummary} />);

    expect(screen.getByText("Total Cost")).toBeInTheDocument();
    expect(screen.getByText("Total Invocations")).toBeInTheDocument();
    expect(screen.getByText("Avg Cost / Invocation")).toBeInTheDocument();
    expect(screen.getByText("Active Flows")).toBeInTheDocument();
  });

  it("renders zero cost correctly", () => {
    const zeroSummary = { ...mockSummary, total_cost_usd: 0 };
    render(<UsageSummaryCards summary={zeroSummary} />);

    expect(screen.getByText("$0.0000")).toBeInTheDocument();
  });
});
