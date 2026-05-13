import { render, screen } from "@testing-library/react";
import { CostTrendChart } from "../CostTrendChart";
import type { DailyCost } from "@/types/usage";

// Note: recharts ResponsiveContainer requires real DOM dimensions.
// Tests that render the actual chart may need a mock for ResponsiveContainer.
// These tests focus on empty states and truncation which don't require chart rendering.

const mockDailyCosts: DailyCost[] = [
  { date: "2026-03-15", cost_usd: 0.0107, invocations: 5 },
  { date: "2026-03-16", cost_usd: 0.025, invocations: 12 },
  { date: "2026-03-17", cost_usd: 0.0, invocations: 0 },
  { date: "2026-03-18", cost_usd: 0.0432, invocations: 8 },
  { date: "2026-03-19", cost_usd: 0.018, invocations: 3 },
];

describe("CostTrendChart", () => {
  it("renders empty state when dailyCosts is undefined", () => {
    render(<CostTrendChart />);
    expect(screen.getByText("No trend data available")).toBeInTheDocument();
  });

  it("renders empty state when dailyCosts is an empty array", () => {
    render(<CostTrendChart dailyCosts={[]} />);
    expect(screen.getByText("No trend data available")).toBeInTheDocument();
  });

  it("does not crash with data provided", () => {
    expect(() => {
      render(<CostTrendChart dailyCosts={mockDailyCosts} />);
    }).not.toThrow();
  });

  it("does not crash with a single data point", () => {
    expect(() => {
      render(<CostTrendChart dailyCosts={[mockDailyCosts[0]]} />);
    }).not.toThrow();
  });

  it("shows truncated warning when truncated is true", () => {
    render(<CostTrendChart dailyCosts={mockDailyCosts} truncated={true} />);
    expect(
      screen.getByText("Data may be incomplete — showing up to 10,000 traces")
    ).toBeInTheDocument();
  });

  it("does not show truncated warning when truncated is false", () => {
    render(<CostTrendChart dailyCosts={mockDailyCosts} truncated={false} />);
    expect(
      screen.queryByText("Data may be incomplete — showing up to 10,000 traces")
    ).not.toBeInTheDocument();
  });
});
