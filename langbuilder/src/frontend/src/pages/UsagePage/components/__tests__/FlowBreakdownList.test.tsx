import { render, screen, fireEvent } from "@testing-library/react";
import { FlowBreakdownList } from "../FlowBreakdownList";
import type { FlowUsage } from "@/types/usage";

// Mock FlowBreakdownRow to isolate FlowBreakdownList
jest.mock("../FlowBreakdownRow", () => ({
  FlowBreakdownRow: ({
    flow,
    onExpand,
  }: {
    flow: FlowUsage;
    onExpand: (flowId: string) => void;
  }) => (
    <tr data-testid={`flow-row-${flow.flow_id}`}>
      <td>{flow.flow_name}</td>
      <td>
        <button
          data-testid={`expand-btn-${flow.flow_id}`}
          onClick={() => onExpand(flow.flow_id)}
        >
          Expand
        </button>
      </td>
    </tr>
  ),
}));

function makeFlow(index: number): FlowUsage {
  return {
    flow_id: `flow-${index}`,
    flow_name: `Flow ${index}`,
    total_cost_usd: 1.5,
    invocation_count: 10,
    avg_cost_per_invocation_usd: 0.15,
    owner_user_id: "user-1",
    owner_username: "testuser",
  };
}

const makeFlows = (count: number): FlowUsage[] =>
  Array.from({ length: count }, (_, i) => makeFlow(i + 1));

describe("FlowBreakdownList", () => {
  it("renders correct number of rows for small list", () => {
    const flows = makeFlows(5);
    render(<FlowBreakdownList flows={flows} onFlowExpand={jest.fn()} />);

    flows.forEach((flow) => {
      expect(screen.getByTestId(`flow-row-${flow.flow_id}`)).toBeInTheDocument();
    });
  });

  it("pagination: shows only 50 per page when list exceeds 50", () => {
    const flows = makeFlows(75);
    render(<FlowBreakdownList flows={flows} onFlowExpand={jest.fn()} />);

    // First 50 are visible
    expect(screen.getByTestId("flow-row-flow-1")).toBeInTheDocument();
    expect(screen.getByTestId("flow-row-flow-50")).toBeInTheDocument();
    // 51st is not visible
    expect(screen.queryByTestId("flow-row-flow-51")).not.toBeInTheDocument();
  });

  it("pagination: Next button shows next page of results", () => {
    const flows = makeFlows(75);
    render(<FlowBreakdownList flows={flows} onFlowExpand={jest.fn()} />);

    const nextBtn = screen.getByTestId("pagination-next");
    fireEvent.click(nextBtn);

    // Page 2 items visible
    expect(screen.getByTestId("flow-row-flow-51")).toBeInTheDocument();
    expect(screen.getByTestId("flow-row-flow-75")).toBeInTheDocument();
    // Page 1 items not visible
    expect(screen.queryByTestId("flow-row-flow-1")).not.toBeInTheDocument();
  });

  it("pagination: Previous button returns to previous page", () => {
    const flows = makeFlows(75);
    render(<FlowBreakdownList flows={flows} onFlowExpand={jest.fn()} />);

    const nextBtn = screen.getByTestId("pagination-next");
    fireEvent.click(nextBtn);

    const prevBtn = screen.getByTestId("pagination-prev");
    fireEvent.click(prevBtn);

    expect(screen.getByTestId("flow-row-flow-1")).toBeInTheDocument();
    expect(screen.queryByTestId("flow-row-flow-51")).not.toBeInTheDocument();
  });

  it("shows 'No flows found' when flows array is empty", () => {
    render(<FlowBreakdownList flows={[]} onFlowExpand={jest.fn()} />);

    expect(screen.getByText("No flows found")).toBeInTheDocument();
  });

  it("flow row expand button calls onFlowExpand callback with flowId", () => {
    const onFlowExpand = jest.fn();
    const flows = makeFlows(2);
    render(<FlowBreakdownList flows={flows} onFlowExpand={onFlowExpand} />);

    fireEvent.click(screen.getByTestId("expand-btn-flow-1"));
    expect(onFlowExpand).toHaveBeenCalledWith("flow-1");
  });

  it("renders table headers", () => {
    const flows = makeFlows(1);
    render(<FlowBreakdownList flows={flows} onFlowExpand={jest.fn()} />);

    expect(screen.getByText("Flow")).toBeInTheDocument();
    expect(screen.getByText("Total Cost")).toBeInTheDocument();
    expect(screen.getByText("Invocations")).toBeInTheDocument();
    expect(screen.getByText("Avg Cost")).toBeInTheDocument();
  });
});
