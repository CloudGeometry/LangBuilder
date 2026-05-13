import { render, screen } from "@testing-library/react";
import { FlowRunsTable } from "../FlowRunsTable";
import type { FlowRunsResponse } from "@/types/usage";

// Mock the hook
const mockUseGetFlowRuns = jest.fn();
jest.mock("../../hooks/useGetFlowRuns", () => ({
  useGetFlowRuns: (flowId: string, params: unknown) =>
    mockUseGetFlowRuns(flowId, params),
}));

const mockRuns: FlowRunsResponse = {
  flow_id: "flow-abc",
  flow_name: "Test Flow",
  runs: [
    {
      run_id: "lw_trace_abc123def456",
      started_at: "2026-03-16T14:32:00Z",
      cost_usd: 0.55,
      input_tokens: 1240,
      output_tokens: 380,
      total_tokens: 1620,
      model: "gpt-4o",
      duration_ms: 2340,
      status: "success",
    },
    {
      run_id: "lw_trace_def456ghi789",
      started_at: "2026-03-16T11:14:00Z",
      cost_usd: 0.42,
      input_tokens: 980,
      output_tokens: 290,
      total_tokens: 1270,
      model: "gpt-4o",
      duration_ms: 1890,
      status: "error",
    },
  ],
  total_runs_in_period: 2,
};

describe("FlowRunsTable", () => {
  beforeEach(() => {
    mockUseGetFlowRuns.mockReset();
  });

  it("renders loading state initially", () => {
    mockUseGetFlowRuns.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });

    render(
      <table>
        <tbody>
          <FlowRunsTable flowId="flow-abc" dateRange={{ from: null, to: null }} />
        </tbody>
      </table>,
    );

    expect(screen.getByTestId("flow-runs-loading")).toBeInTheDocument();
    expect(screen.getByText(/loading runs/i)).toBeInTheDocument();
  });

  it("renders runs when data is available", () => {
    mockUseGetFlowRuns.mockReturnValue({
      data: mockRuns,
      isLoading: false,
      isError: false,
    });

    render(
      <table>
        <tbody>
          <FlowRunsTable flowId="flow-abc" dateRange={{ from: null, to: null }} />
        </tbody>
      </table>,
    );

    expect(
      screen.getByTestId("run-row-lw_trace_abc123def456"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("run-row-lw_trace_def456ghi789"),
    ).toBeInTheDocument();
  });

  it("shows error state on fetch failure", () => {
    mockUseGetFlowRuns.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    render(
      <table>
        <tbody>
          <FlowRunsTable flowId="flow-abc" dateRange={{ from: null, to: null }} />
        </tbody>
      </table>,
    );

    expect(screen.getByTestId("flow-runs-error")).toBeInTheDocument();
    expect(screen.getByText(/failed to load run data/i)).toBeInTheDocument();
  });

  it("shows empty message when no runs in period", () => {
    mockUseGetFlowRuns.mockReturnValue({
      data: { ...mockRuns, runs: [] },
      isLoading: false,
      isError: false,
    });

    render(
      <table>
        <tbody>
          <FlowRunsTable flowId="flow-abc" dateRange={{ from: null, to: null }} />
        </tbody>
      </table>,
    );

    expect(screen.getByTestId("flow-runs-empty")).toBeInTheDocument();
    expect(screen.getByText(/no runs found/i)).toBeInTheDocument();
  });

  it("passes correct params to hook", () => {
    mockUseGetFlowRuns.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });

    render(
      <table>
        <tbody>
          <FlowRunsTable
            flowId="flow-xyz"
            dateRange={{ from: "2026-03-01", to: "2026-03-16" }}
          />
        </tbody>
      </table>,
    );

    expect(mockUseGetFlowRuns).toHaveBeenCalledWith("flow-xyz", {
      from_date: "2026-03-01",
      to_date: "2026-03-16",
    });
  });

  it("truncates long run IDs", () => {
    mockUseGetFlowRuns.mockReturnValue({
      data: mockRuns,
      isLoading: false,
      isError: false,
    });

    render(
      <table>
        <tbody>
          <FlowRunsTable flowId="flow-abc" dateRange={{ from: null, to: null }} />
        </tbody>
      </table>,
    );

    // Full run_id is "lw_trace_abc123def456" - length 21, should be truncated
    const fullId = "lw_trace_abc123def456";
    expect(screen.queryByText(fullId)).not.toBeInTheDocument();
  });

  it("displays status badge for each run", () => {
    mockUseGetFlowRuns.mockReturnValue({
      data: mockRuns,
      isLoading: false,
      isError: false,
    });

    render(
      <table>
        <tbody>
          <FlowRunsTable flowId="flow-abc" dateRange={{ from: null, to: null }} />
        </tbody>
      </table>,
    );

    expect(screen.getByText("success")).toBeInTheDocument();
    expect(screen.getByText("error")).toBeInTheDocument();
  });
});
