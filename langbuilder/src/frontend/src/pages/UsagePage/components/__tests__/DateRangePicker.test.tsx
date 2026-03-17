import { render, screen, fireEvent } from "@testing-library/react";
import { DateRangePicker, formatDisplayRange } from "../DateRangePicker";

// Mock lucide-react
jest.mock("lucide-react", () => ({
  CalendarIcon: () => <span data-testid="calendar-icon" />,
}));

// Mock UI components
jest.mock("@/components/ui/button", () => ({
  Button: ({
    children,
    onClick,
    "data-testid": testId,
    ...rest
  }: {
    children?: React.ReactNode;
    onClick?: () => void;
    "data-testid"?: string;
    [key: string]: unknown;
  }) => (
    <button onClick={onClick} data-testid={testId} {...(rest as object)}>
      {children}
    </button>
  ),
}));

jest.mock("@/components/ui/popover", () => ({
  Popover: ({
    children,
    open,
  }: {
    children: React.ReactNode;
    open?: boolean;
  }) => (
    <div data-testid="popover" data-open={open}>
      {children}
    </div>
  ),
  PopoverTrigger: ({
    children,
  }: {
    children: React.ReactNode;
    asChild?: boolean;
  }) => <div data-testid="popover-trigger">{children}</div>,
  PopoverContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="popover-content">{children}</div>
  ),
}));

describe("DateRangePicker", () => {
  const mockOnChange = jest.fn();

  beforeEach(() => {
    mockOnChange.mockReset();
  });

  it("renders all 4 preset buttons", () => {
    render(
      <DateRangePicker value={{ from: null, to: null }} onChange={mockOnChange} />,
    );

    expect(
      screen.getByTestId("preset-last-24h"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("preset-last-7-days"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("preset-last-14-days"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("preset-last-30-days"),
    ).toBeInTheDocument();
  });

  it("calls onChange with date range when Last 7 days preset is clicked", () => {
    render(
      <DateRangePicker value={{ from: null, to: null }} onChange={mockOnChange} />,
    );

    fireEvent.click(screen.getByTestId("preset-last-7-days"));

    expect(mockOnChange).toHaveBeenCalledTimes(1);
    const callArg = mockOnChange.mock.calls[0][0];
    expect(callArg.from).toBeDefined();
    expect(callArg.to).toBeDefined();
    // from should be a valid ISO date (YYYY-MM-DD format)
    expect(callArg.from).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(callArg.to).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    // from should be before to
    expect(new Date(callArg.from) < new Date(callArg.to)).toBe(true);
  });

  it("clear button is not visible when no dates are set", () => {
    render(
      <DateRangePicker value={{ from: null, to: null }} onChange={mockOnChange} />,
    );

    expect(screen.queryByTestId("date-clear-button")).not.toBeInTheDocument();
  });

  it("clear button is visible when from date is set", () => {
    render(
      <DateRangePicker
        value={{ from: "2025-01-01", to: null }}
        onChange={mockOnChange}
      />,
    );

    expect(screen.getByTestId("date-clear-button")).toBeInTheDocument();
  });

  it("clear button is visible when to date is set", () => {
    render(
      <DateRangePicker
        value={{ from: null, to: "2025-12-31" }}
        onChange={mockOnChange}
      />,
    );

    expect(screen.getByTestId("date-clear-button")).toBeInTheDocument();
  });

  it("calls onChange with null dates when clear is clicked", () => {
    render(
      <DateRangePicker
        value={{ from: "2025-01-01", to: "2025-12-31" }}
        onChange={mockOnChange}
      />,
    );

    fireEvent.click(screen.getByTestId("date-clear-button"));

    expect(mockOnChange).toHaveBeenCalledWith({ from: null, to: null });
  });
});

describe("formatDisplayRange", () => {
  it("returns 'All time' when no dates set", () => {
    expect(formatDisplayRange(null, null)).toBe("All time");
  });

  it("returns formatted range when both dates set", () => {
    expect(formatDisplayRange("2025-01-01", "2025-12-31")).toBe(
      "2025-01-01 \u2013 2025-12-31",
    );
  });

  it("returns 'From ...' when only from date set", () => {
    expect(formatDisplayRange("2025-01-01", null)).toBe("From 2025-01-01");
  });

  it("returns 'Until ...' when only to date set", () => {
    expect(formatDisplayRange(null, "2025-12-31")).toBe("Until 2025-12-31");
  });
});
