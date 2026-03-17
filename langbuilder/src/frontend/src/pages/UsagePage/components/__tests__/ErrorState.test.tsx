import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorState } from "../ErrorState";

describe("ErrorState", () => {
  it("renders timeout error message correctly", () => {
    const error = { detail: { code: "LANGWATCH_TIMEOUT" } };
    render(<ErrorState error={error} onRetry={jest.fn()} />);

    expect(
      screen.getByText(/langwatch took too long to respond/i),
    ).toBeInTheDocument();
  });

  it("renders unavailable error message", () => {
    const error = { detail: { code: "LANGWATCH_UNAVAILABLE" } };
    render(<ErrorState error={error} onRetry={jest.fn()} />);

    expect(
      screen.getByText(/langwatch is temporarily unavailable/i),
    ).toBeInTheDocument();
  });

  it("renders key not configured message", () => {
    const error = { detail: { code: "KEY_NOT_CONFIGURED" } };
    render(<ErrorState error={error} onRetry={jest.fn()} />);

    expect(
      screen.getByText(/langwatch api key not configured/i),
    ).toBeInTheDocument();
  });

  it("renders unknown error message for unrecognized codes", () => {
    const error = { detail: { code: "SOME_UNKNOWN_CODE" } };
    render(<ErrorState error={error} onRetry={jest.fn()} />);

    expect(
      screen.getByText(/an unexpected error occurred/i),
    ).toBeInTheDocument();
  });

  it("retry button calls onRetry when retryable is true (default)", () => {
    const onRetry = jest.fn();
    const error = { detail: { code: "LANGWATCH_UNAVAILABLE" } };
    render(<ErrorState error={error} onRetry={onRetry} />);

    fireEvent.click(screen.getByTestId("retry-button"));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("retry button is hidden when retryable is false", () => {
    const error = { detail: { code: "LANGWATCH_UNAVAILABLE" } };
    render(<ErrorState error={error} onRetry={jest.fn()} retryable={false} />);

    expect(screen.queryByTestId("retry-button")).not.toBeInTheDocument();
  });

  it("handles null/undefined error gracefully", () => {
    render(<ErrorState error={null} onRetry={jest.fn()} />);

    expect(
      screen.getByText(/an unexpected error occurred/i),
    ).toBeInTheDocument();
  });
});
