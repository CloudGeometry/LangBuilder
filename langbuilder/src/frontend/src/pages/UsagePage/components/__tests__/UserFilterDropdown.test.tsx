import { render, screen, fireEvent } from "@testing-library/react";
import { UserFilterDropdown } from "../UserFilterDropdown";

const mockUsers = [
  { id: "user-1", username: "alice" },
  { id: "user-2", username: "bob" },
  { id: "user-3", username: "charlie" },
];

describe("UserFilterDropdown", () => {
  const mockOnChange = jest.fn();

  beforeEach(() => {
    mockOnChange.mockReset();
  });

  it("renders dropdown with users", () => {
    render(
      <UserFilterDropdown
        value={null}
        onChange={mockOnChange}
        users={mockUsers}
      />,
    );

    expect(screen.getByTestId("user-filter-dropdown")).toBeInTheDocument();
  });

  it("renders 'All users' option as first option", () => {
    render(
      <UserFilterDropdown
        value={null}
        onChange={mockOnChange}
        users={mockUsers}
      />,
    );

    expect(screen.getByText("All users")).toBeInTheDocument();
  });

  it("renders all user options", () => {
    render(
      <UserFilterDropdown
        value={null}
        onChange={mockOnChange}
        users={mockUsers}
      />,
    );

    expect(screen.getByText("alice")).toBeInTheDocument();
    expect(screen.getByText("bob")).toBeInTheDocument();
    expect(screen.getByText("charlie")).toBeInTheDocument();
  });

  it("calls onChange with userId when user is selected", () => {
    render(
      <UserFilterDropdown
        value={null}
        onChange={mockOnChange}
        users={mockUsers}
      />,
    );

    fireEvent.change(screen.getByTestId("user-filter-dropdown"), {
      target: { value: "user-1" },
    });

    expect(mockOnChange).toHaveBeenCalledWith("user-1");
  });

  it("calls onChange with null when 'All users' is selected", () => {
    render(
      <UserFilterDropdown
        value="user-1"
        onChange={mockOnChange}
        users={mockUsers}
      />,
    );

    fireEvent.change(screen.getByTestId("user-filter-dropdown"), {
      target: { value: "" },
    });

    expect(mockOnChange).toHaveBeenCalledWith(null);
  });

  it("shows selected user in dropdown", () => {
    render(
      <UserFilterDropdown
        value="user-2"
        onChange={mockOnChange}
        users={mockUsers}
      />,
    );

    const select = screen.getByTestId(
      "user-filter-dropdown",
    ) as HTMLSelectElement;
    expect(select.value).toBe("user-2");
  });

  it("renders with empty users list", () => {
    render(
      <UserFilterDropdown value={null} onChange={mockOnChange} users={[]} />,
    );

    expect(screen.getByTestId("user-filter-dropdown")).toBeInTheDocument();
    expect(screen.getByText("All users")).toBeInTheDocument();
  });
});
