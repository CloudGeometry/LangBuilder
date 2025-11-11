import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import AssignmentListView from "../AssignmentListView";

// Mock IconComponent
jest.mock("@/components/common/genericIconComponent", () => {
  return function MockIconComponent({ name, className }: any) {
    return <span data-testid={`icon-${name}`} className={className} />;
  };
});

// Mock CustomLoader
jest.mock("@/customization/components/custom-loader", () => {
  return function MockCustomLoader({ remSize }: any) {
    return <div data-testid="custom-loader">Loading...</div>;
  };
});

// Mock Button component
jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, disabled, ...props }: any) => (
    <button onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  ),
}));

// Mock Input component
jest.mock("@/components/ui/input", () => ({
  Input: ({ value, onChange, placeholder, ...props }: any) => (
    <input
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      {...props}
    />
  ),
}));

// Mock Table components
jest.mock("@/components/ui/table", () => ({
  Table: ({ children }: any) => <table>{children}</table>,
  TableHeader: ({ children }: any) => <thead>{children}</thead>,
  TableBody: ({ children }: any) => <tbody>{children}</tbody>,
  TableRow: ({ children }: any) => <tr>{children}</tr>,
  TableHead: ({ children }: any) => <th>{children}</th>,
  TableCell: ({ children }: any) => <td>{children}</td>,
}));

// Mock alertStore
jest.mock("@/stores/alertStore", () => ({
  __esModule: true,
  default: jest.fn(() => ({
    setSuccessData: jest.fn(),
    setErrorData: jest.fn(),
  })),
}));

// Mock API
jest.mock("@/controllers/API", () => ({
  api: {
    get: jest.fn(() => Promise.resolve({ data: [] })),
    delete: jest.fn(() => Promise.resolve({})),
  },
}));

describe("AssignmentListView", () => {
  const mockOnEditAssignment = jest.fn();
  let queryClient: QueryClient;

  const renderWithProviders = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>,
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Create a new QueryClient for each test to ensure isolation
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false, // Disable retries in tests
          gcTime: 0, // Disable caching in tests
        },
        mutations: {
          retry: false,
        },
      },
    });
  });

  describe("Rendering", () => {
    it("should render filter inputs", () => {
      renderWithProviders(
        <AssignmentListView onEditAssignment={mockOnEditAssignment} />,
      );

      expect(
        screen.getByPlaceholderText("Filter by username..."),
      ).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText("Filter by role..."),
      ).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText("Filter by scope..."),
      ).toBeInTheDocument();
    });

    it("should render empty state when no assignments exist", async () => {
      renderWithProviders(
        <AssignmentListView onEditAssignment={mockOnEditAssignment} />,
      );

      // Wait for the query to resolve
      await waitFor(() => {
        expect(screen.getByTestId("icon-UserCog")).toBeInTheDocument();
      });

      expect(
        screen.getByText(
          "No role assignments found. Create your first assignment.",
        ),
      ).toBeInTheDocument();
    });

    it("should not show clear icons when filters are empty", () => {
      renderWithProviders(
        <AssignmentListView onEditAssignment={mockOnEditAssignment} />,
      );

      expect(screen.queryByTestId("icon-X")).not.toBeInTheDocument();
    });
  });

  describe("Filter functionality", () => {
    it("should show clear icon when username filter has value", () => {
      renderWithProviders(
        <AssignmentListView onEditAssignment={mockOnEditAssignment} />,
      );

      const usernameInput = screen.getByPlaceholderText(
        "Filter by username...",
      );
      fireEvent.change(usernameInput, { target: { value: "testuser" } });

      const clearIcons = screen.getAllByTestId("icon-X");
      expect(clearIcons.length).toBeGreaterThan(0);
    });

    it("should show clear icon when role filter has value", () => {
      renderWithProviders(
        <AssignmentListView onEditAssignment={mockOnEditAssignment} />,
      );

      const roleInput = screen.getByPlaceholderText("Filter by role...");
      fireEvent.change(roleInput, { target: { value: "admin" } });

      const clearIcons = screen.getAllByTestId("icon-X");
      expect(clearIcons.length).toBeGreaterThan(0);
    });

    it("should show clear icon when scope filter has value", () => {
      renderWithProviders(
        <AssignmentListView onEditAssignment={mockOnEditAssignment} />,
      );

      const scopeInput = screen.getByPlaceholderText("Filter by scope...");
      fireEvent.change(scopeInput, { target: { value: "project" } });

      const clearIcons = screen.getAllByTestId("icon-X");
      expect(clearIcons.length).toBeGreaterThan(0);
    });

    it("should clear filter when clear icon is clicked", () => {
      renderWithProviders(
        <AssignmentListView onEditAssignment={mockOnEditAssignment} />,
      );

      const usernameInput = screen.getByPlaceholderText(
        "Filter by username...",
      ) as HTMLInputElement;
      fireEvent.change(usernameInput, { target: { value: "testuser" } });

      expect(usernameInput.value).toBe("testuser");

      const clearIcon = screen.getAllByTestId("icon-X")[0];
      fireEvent.click(clearIcon.parentElement!);

      expect(usernameInput.value).toBe("");
    });

    it("should update filter state when input changes", () => {
      renderWithProviders(
        <AssignmentListView onEditAssignment={mockOnEditAssignment} />,
      );

      const usernameInput = screen.getByPlaceholderText(
        "Filter by username...",
      ) as HTMLInputElement;
      const roleInput = screen.getByPlaceholderText(
        "Filter by role...",
      ) as HTMLInputElement;
      const scopeInput = screen.getByPlaceholderText(
        "Filter by scope...",
      ) as HTMLInputElement;

      fireEvent.change(usernameInput, { target: { value: "alice" } });
      fireEvent.change(roleInput, { target: { value: "editor" } });
      fireEvent.change(scopeInput, { target: { value: "flow" } });

      expect(usernameInput.value).toBe("alice");
      expect(roleInput.value).toBe("editor");
      expect(scopeInput.value).toBe("flow");
    });
  });

  describe("Loading state", () => {
    it("should not show loader when not loading", async () => {
      renderWithProviders(
        <AssignmentListView onEditAssignment={mockOnEditAssignment} />,
      );

      // Wait for the query to resolve
      await waitFor(() => {
        expect(screen.queryByTestId("custom-loader")).not.toBeInTheDocument();
      });
    });
  });

  describe("Empty state messages", () => {
    it("should show appropriate message when no assignments exist", async () => {
      renderWithProviders(
        <AssignmentListView onEditAssignment={mockOnEditAssignment} />,
      );

      // Wait for the query to resolve
      await waitFor(() => {
        expect(
          screen.getByText(
            "No role assignments found. Create your first assignment.",
          ),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Accessibility", () => {
    it("should have accessible filter inputs with placeholders", () => {
      renderWithProviders(
        <AssignmentListView onEditAssignment={mockOnEditAssignment} />,
      );

      const usernameInput = screen.getByPlaceholderText(
        "Filter by username...",
      );
      const roleInput = screen.getByPlaceholderText("Filter by role...");
      const scopeInput = screen.getByPlaceholderText("Filter by scope...");

      expect(usernameInput).toBeInTheDocument();
      expect(roleInput).toBeInTheDocument();
      expect(scopeInput).toBeInTheDocument();
    });
  });
});
