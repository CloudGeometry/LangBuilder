import { render, screen } from "@testing-library/react";
import { EmptyStatePrompt } from "../EmptyStatePrompt";

describe("EmptyStatePrompt", () => {
  it("renders no_key variant with correct text", () => {
    render(<EmptyStatePrompt variant="no_key" isAdmin={false} />);

    expect(
      screen.getByText(/langwatch api key not configured/i),
    ).toBeInTheDocument();
  });

  it("admin sees settings link in no_key variant", () => {
    render(<EmptyStatePrompt variant="no_key" isAdmin={true} />);

    expect(
      screen.getByTestId("admin-settings-link"),
    ).toBeInTheDocument();
  });

  it("non-admin sees different message in no_key variant", () => {
    render(<EmptyStatePrompt variant="no_key" isAdmin={false} />);

    expect(
      screen.getByTestId("non-admin-message"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("admin-settings-link"),
    ).not.toBeInTheDocument();
  });

  it("renders no_data variant with correct text", () => {
    render(<EmptyStatePrompt variant="no_data" isAdmin={false} />);

    expect(
      screen.getByText(/no usage data found for this period/i),
    ).toBeInTheDocument();
  });

  it("no_data variant suggests adjusting date range", () => {
    render(<EmptyStatePrompt variant="no_data" isAdmin={false} />);

    expect(screen.getByText(/adjust/i)).toBeInTheDocument();
  });

  it("no_data variant renders correct testid", () => {
    render(<EmptyStatePrompt variant="no_data" isAdmin={true} />);

    expect(screen.getByTestId("empty-state-no-data")).toBeInTheDocument();
  });

  it("no_key variant renders correct testid", () => {
    render(<EmptyStatePrompt variant="no_key" isAdmin={false} />);

    expect(screen.getByTestId("empty-state-no-key")).toBeInTheDocument();
  });
});
