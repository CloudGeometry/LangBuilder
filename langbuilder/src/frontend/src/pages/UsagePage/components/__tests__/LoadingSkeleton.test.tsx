import { render, screen } from "@testing-library/react";
import { UsageLoadingSkeleton } from "../LoadingSkeleton";

// Mock the Skeleton component
jest.mock("@/components/ui/skeleton", () => ({
  Skeleton: ({ className }: { className?: string }) => (
    <div data-testid="skeleton" className={className} />
  ),
}));

describe("UsageLoadingSkeleton", () => {
  it("renders with data-testid attribute", () => {
    render(<UsageLoadingSkeleton />);

    expect(screen.getByTestId("usage-loading-skeleton")).toBeInTheDocument();
  });

  it("renders 4 summary card placeholders", () => {
    render(<UsageLoadingSkeleton />);

    // 4 summary cards, each with 2 skeletons = 8 skeletons from summary cards
    // Plus filter bar skeletons (2) + table header skeleton (1) + table row skeletons (5 * 4 = 20)
    // Total = 31 skeletons, but we just check we have at least 8 from summary cards
    const skeletons = screen.getAllByTestId("skeleton");
    expect(skeletons.length).toBeGreaterThanOrEqual(8);
  });

  it("renders 4 card containers in the summary section", () => {
    const { container } = render(<UsageLoadingSkeleton />);

    // The 4 card containers
    const grid = container.querySelector(".grid.grid-cols-4");
    expect(grid).toBeInTheDocument();
    const cards = grid?.querySelectorAll(".rounded-lg.border");
    expect(cards?.length).toBe(4);
  });

  it("renders 5 table row placeholders", () => {
    const { container } = render(<UsageLoadingSkeleton />);

    // The table section is the last .rounded-lg.border container (after the 4 cards)
    const allBorderContainers = container.querySelectorAll(".rounded-lg.border");
    // There are 4 card containers inside the grid + 1 table container = 5 total
    // The last one is the table
    const tableContainer = allBorderContainers[allBorderContainers.length - 1];
    const rows = tableContainer?.querySelectorAll(".flex.gap-4");
    expect(rows?.length).toBe(5);
  });

  it("renders filter bar placeholders", () => {
    const { container } = render(<UsageLoadingSkeleton />);

    const filterBar = container.querySelector(".flex.gap-4");
    expect(filterBar).toBeInTheDocument();
  });
});
