import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import * as API from "@/controllers/API";
import useAlertStore from "@/stores/alertStore";
import EditAssignmentModal from "../EditAssignmentModal";

// Mock API
jest.mock("@/controllers/API", () => ({
  api: {
    get: jest.fn(),
    patch: jest.fn(),
  },
}));

// Mock alert store
const mockSetSuccessData = jest.fn();
const mockSetErrorData = jest.fn();

jest.mock("@/stores/alertStore", () => ({
  __esModule: true,
  default: jest.fn((selector) => {
    const store = {
      setSuccessData: mockSetSuccessData,
      setErrorData: mockSetErrorData,
    };
    return selector ? selector(store) : store;
  }),
}));

// Mock CustomLoader
jest.mock("@/customization/components/custom-loader", () => ({
  __esModule: true,
  default: () => <div data-testid="loader">Loading...</div>,
}));

describe("EditAssignmentModal", () => {
  let queryClient: QueryClient;
  let mockOnClose: jest.Mock;
  let mockOnSuccess: jest.Mock;

  const mockAssignment = {
    id: "assignment-123",
    user_id: "user-123",
    username: "testuser",
    role_name: "Admin",
    scope_type: "Project",
    scope_id: "project-456",
    scope_name: "Test Project",
    is_immutable: false,
    created_at: "2025-01-01T00:00:00Z",
  };

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    mockOnClose = jest.fn();
    mockOnSuccess = jest.fn();

    jest.clearAllMocks();
  });

  const renderModal = (open = true, assignmentId = "assignment-123") => {
    return render(
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <EditAssignmentModal
            open={open}
            assignmentId={assignmentId}
            onClose={mockOnClose}
            onSuccess={mockOnSuccess}
          />
        </TooltipProvider>
      </QueryClientProvider>,
    );
  };

  describe("Rendering", () => {
    it("should render modal when open", () => {
      (API.api.get as any).mockResolvedValueOnce({
        data: mockAssignment,
      });

      renderModal();
      expect(screen.getByText("Edit Role Assignment")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Update the role assignment details. User cannot be changed.",
        ),
      ).toBeInTheDocument();
    });

    it("should not render modal when closed", () => {
      renderModal(false);
      expect(
        screen.queryByText("Edit Role Assignment"),
      ).not.toBeInTheDocument();
    });

    it("should show loader while fetching assignment", () => {
      (API.api.get as any).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve({ data: mockAssignment }), 100),
          ),
      );

      renderModal();
      expect(screen.getByTestId("loader")).toBeInTheDocument();
    });

    it("should render form fields after loading", async () => {
      (API.api.get as any).mockResolvedValueOnce({
        data: mockAssignment,
      });

      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText("Role")).toBeInTheDocument();
        expect(screen.getByLabelText("Scope Type")).toBeInTheDocument();
        expect(
          screen.getByLabelText("Scope ID (optional)"),
        ).toBeInTheDocument();
      });
    });

    it("should render action buttons", async () => {
      (API.api.get as any).mockResolvedValueOnce({
        data: mockAssignment,
      });

      renderModal();

      await waitFor(() => {
        expect(screen.getByText("Cancel")).toBeInTheDocument();
        expect(screen.getByText("Save Changes")).toBeInTheDocument();
      });
    });
  });

  describe("Data Fetching", () => {
    it("should fetch assignment details on open", async () => {
      (API.api.get as any).mockResolvedValueOnce({
        data: mockAssignment,
      });

      renderModal();

      await waitFor(() => {
        expect(API.api.get).toHaveBeenCalledWith(
          "/api/v1/rbac/assignments/assignment-123",
        );
      });
    });

    it("should not fetch when modal is closed", () => {
      renderModal(false);
      expect(API.api.get).not.toHaveBeenCalled();
    });

    it("should populate form fields with fetched data", async () => {
      (API.api.get as any).mockResolvedValueOnce({
        data: mockAssignment,
      });

      renderModal();

      await waitFor(() => {
        const roleInput = screen.getByLabelText("Role") as HTMLInputElement;
        const scopeTypeInput = screen.getByLabelText(
          "Scope Type",
        ) as HTMLInputElement;
        const scopeIdInput = screen.getByLabelText(
          "Scope ID (optional)",
        ) as HTMLInputElement;

        expect(roleInput.value).toBe("Admin");
        expect(scopeTypeInput.value).toBe("Project");
        expect(scopeIdInput.value).toBe("project-456");
      });
    });
  });

  describe("User Interactions", () => {
    beforeEach(() => {
      (API.api.get as any).mockResolvedValueOnce({
        data: mockAssignment,
      });
    });

    it("should update roleName field on input", async () => {
      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText("Role")).toBeInTheDocument();
      });

      const roleInput = screen.getByLabelText("Role");
      fireEvent.change(roleInput, { target: { value: "Editor" } });
      expect(roleInput).toHaveValue("Editor");
    });

    it("should update scopeType field on input", async () => {
      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText("Scope Type")).toBeInTheDocument();
      });

      const scopeTypeInput = screen.getByLabelText("Scope Type");
      fireEvent.change(scopeTypeInput, {
        target: { value: "Flow" },
      });
      expect(scopeTypeInput).toHaveValue("Flow");
    });

    it("should update scopeId field on input", async () => {
      renderModal();

      await waitFor(() => {
        expect(
          screen.getByLabelText("Scope ID (optional)"),
        ).toBeInTheDocument();
      });

      const scopeIdInput = screen.getByLabelText("Scope ID (optional)");
      fireEvent.change(scopeIdInput, {
        target: { value: "flow-789" },
      });
      expect(scopeIdInput).toHaveValue("flow-789");
    });

    it("should call onClose when Cancel button is clicked", async () => {
      renderModal();

      await waitFor(() => {
        expect(screen.getByText("Cancel")).toBeInTheDocument();
      });

      const cancelButton = screen.getByText("Cancel");
      fireEvent.click(cancelButton);
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  describe("Validation", () => {
    beforeEach(() => {
      (API.api.get as any).mockResolvedValueOnce({
        data: mockAssignment,
      });
    });

    it("should show error when required fields are missing", async () => {
      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText("Role")).toBeInTheDocument();
      });

      const roleInput = screen.getByLabelText("Role");
      fireEvent.change(roleInput, { target: { value: "" } });

      const submitButton = screen.getByText("Save Changes");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockSetErrorData).toHaveBeenCalledWith({
          title: "Validation Error",
          list: ["Role and Scope Type are required"],
        });
      });

      expect(API.api.patch).not.toHaveBeenCalled();
    });

    it("should show error when scopeId is missing for non-Global scope", async () => {
      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText("Scope Type")).toBeInTheDocument();
      });

      const scopeTypeInput = screen.getByLabelText("Scope Type");
      const scopeIdInput = screen.getByLabelText("Scope ID (optional)");

      fireEvent.change(scopeTypeInput, {
        target: { value: "Project" },
      });
      fireEvent.change(scopeIdInput, { target: { value: "" } });

      const submitButton = screen.getByText("Save Changes");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockSetErrorData).toHaveBeenCalledWith({
          title: "Validation Error",
          list: ["Scope ID is required for Project and Flow scopes"],
        });
      });
    });

    it("should show error when scopeId is provided for Global scope", async () => {
      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText("Scope Type")).toBeInTheDocument();
      });

      const scopeTypeInput = screen.getByLabelText("Scope Type");
      const scopeIdInput = screen.getByLabelText("Scope ID (optional)");

      fireEvent.change(scopeTypeInput, {
        target: { value: "Global" },
      });
      fireEvent.change(scopeIdInput, {
        target: { value: "should-be-empty" },
      });

      const submitButton = screen.getByText("Save Changes");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockSetErrorData).toHaveBeenCalledWith({
          title: "Validation Error",
          list: ["Scope ID should be empty for Global scope"],
        });
      });
    });
  });

  describe("API Integration", () => {
    beforeEach(() => {
      (API.api.get as any).mockResolvedValueOnce({
        data: mockAssignment,
      });
    });

    it("should call API with correct data on submit", async () => {
      (API.api.patch as any).mockResolvedValueOnce({
        data: { ...mockAssignment, role_name: "Editor" },
      });

      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText("Role")).toBeInTheDocument();
      });

      const roleInput = screen.getByLabelText("Role");
      fireEvent.change(roleInput, { target: { value: "Editor" } });

      const submitButton = screen.getByText("Save Changes");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(API.api.patch).toHaveBeenCalledWith(
          "/api/v1/rbac/assignments/assignment-123",
          {
            role_name: "Editor",
            scope_type: "Project",
            scope_id: "project-456",
          },
        );
      });
    });

    it("should call API with null scope_id for Global scope", async () => {
      (API.api.patch as any).mockResolvedValueOnce({
        data: {
          ...mockAssignment,
          scope_type: "Global",
          scope_id: null,
        },
      });

      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText("Scope Type")).toBeInTheDocument();
      });

      const scopeTypeInput = screen.getByLabelText("Scope Type");
      const scopeIdInput = screen.getByLabelText("Scope ID (optional)");

      fireEvent.change(scopeTypeInput, {
        target: { value: "Global" },
      });
      fireEvent.change(scopeIdInput, { target: { value: "" } });

      const submitButton = screen.getByText("Save Changes");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(API.api.patch).toHaveBeenCalledWith(
          "/api/v1/rbac/assignments/assignment-123",
          {
            role_name: "Admin",
            scope_type: "Global",
            scope_id: null,
          },
        );
      });
    });

    it("should show success message on successful update", async () => {
      (API.api.patch as any).mockResolvedValueOnce({
        data: mockAssignment,
      });

      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText("Role")).toBeInTheDocument();
      });

      const submitButton = screen.getByText("Save Changes");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockSetSuccessData).toHaveBeenCalledWith({
          title: "Role assignment updated successfully",
        });
      });
    });

    it("should call onSuccess callback on successful update", async () => {
      (API.api.patch as any).mockResolvedValueOnce({
        data: mockAssignment,
      });

      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText("Role")).toBeInTheDocument();
      });

      const submitButton = screen.getByText("Save Changes");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });

    it("should show error message on API failure", async () => {
      const errorMessage = "Assignment not found";
      (API.api.patch as any).mockRejectedValueOnce({
        response: { data: { detail: errorMessage } },
      });

      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText("Role")).toBeInTheDocument();
      });

      const submitButton = screen.getByText("Save Changes");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockSetErrorData).toHaveBeenCalledWith({
          title: "Failed to update role assignment",
          list: [errorMessage],
        });
      });
    });

    it("should disable buttons during submission", async () => {
      (API.api.patch as any).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve({ data: mockAssignment }), 100),
          ),
      );

      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText("Role")).toBeInTheDocument();
      });

      const submitButton = screen.getByText("Save Changes");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
        expect(screen.getByText("Saving...")).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(mockSetSuccessData).toHaveBeenCalled();
      });
    });
  });

  describe("Query Cache Invalidation", () => {
    beforeEach(() => {
      (API.api.get as any).mockResolvedValueOnce({
        data: mockAssignment,
      });
    });

    it("should invalidate queries on success", async () => {
      (API.api.patch as any).mockResolvedValueOnce({
        data: mockAssignment,
      });

      const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");

      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText("Role")).toBeInTheDocument();
      });

      const submitButton = screen.getByText("Save Changes");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(invalidateSpy).toHaveBeenCalledWith({
          queryKey: ["rbac-assignments"],
        });
        expect(invalidateSpy).toHaveBeenCalledWith({
          queryKey: ["rbac-assignment", "assignment-123"],
        });
      });
    });
  });
});
