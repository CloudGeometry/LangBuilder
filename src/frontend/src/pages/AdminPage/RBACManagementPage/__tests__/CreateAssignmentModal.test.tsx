import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import * as API from "@/controllers/API";
import useAlertStore from "@/stores/alertStore";
import CreateAssignmentModal from "../CreateAssignmentModal";

// Mock API
jest.mock("@/controllers/API", () => ({
  api: {
    post: jest.fn(),
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

describe("CreateAssignmentModal", () => {
  let queryClient: QueryClient;
  let mockOnClose: jest.Mock;
  let mockOnSuccess: jest.Mock;

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

  const renderModal = (open = true) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <CreateAssignmentModal
            open={open}
            onClose={mockOnClose}
            onSuccess={mockOnSuccess}
          />
        </TooltipProvider>
      </QueryClientProvider>,
    );
  };

  describe("Rendering", () => {
    it("should render modal when open", () => {
      renderModal();
      expect(screen.getByText("Create Role Assignment")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Assign a role to a user for a specific scope (Global, Project, or Flow).",
        ),
      ).toBeInTheDocument();
    });

    it("should not render modal when closed", () => {
      renderModal(false);
      expect(
        screen.queryByText("Create Role Assignment"),
      ).not.toBeInTheDocument();
    });

    it("should render all form fields", () => {
      renderModal();
      expect(screen.getByLabelText("User ID")).toBeInTheDocument();
      expect(screen.getByLabelText("Role")).toBeInTheDocument();
      expect(screen.getByLabelText("Scope Type")).toBeInTheDocument();
      expect(screen.getByLabelText("Scope ID (optional)")).toBeInTheDocument();
    });

    it("should render action buttons", () => {
      renderModal();
      expect(screen.getByText("Cancel")).toBeInTheDocument();
      expect(screen.getByText("Create Assignment")).toBeInTheDocument();
    });
  });

  describe("User Interactions", () => {
    it("should update userId field on input", () => {
      renderModal();
      const userIdInput = screen.getByLabelText("User ID");
      fireEvent.change(userIdInput, {
        target: { value: "user-123" },
      });
      expect(userIdInput).toHaveValue("user-123");
    });

    it("should update roleName field on input", () => {
      renderModal();
      const roleInput = screen.getByLabelText("Role");
      fireEvent.change(roleInput, { target: { value: "Admin" } });
      expect(roleInput).toHaveValue("Admin");
    });

    it("should update scopeType field on input", () => {
      renderModal();
      const scopeTypeInput = screen.getByLabelText("Scope Type");
      fireEvent.change(scopeTypeInput, {
        target: { value: "Project" },
      });
      expect(scopeTypeInput).toHaveValue("Project");
    });

    it("should update scopeId field on input", () => {
      renderModal();
      const scopeIdInput = screen.getByLabelText("Scope ID (optional)");
      fireEvent.change(scopeIdInput, {
        target: { value: "project-456" },
      });
      expect(scopeIdInput).toHaveValue("project-456");
    });

    it("should call onClose when Cancel button is clicked", () => {
      renderModal();
      const cancelButton = screen.getByText("Cancel");
      fireEvent.click(cancelButton);
      expect(mockOnClose).toHaveBeenCalled();
    });

    it("should clear form fields when modal is closed", () => {
      renderModal();
      const userIdInput = screen.getByLabelText("User ID");
      const roleInput = screen.getByLabelText("Role");

      fireEvent.change(userIdInput, {
        target: { value: "user-123" },
      });
      fireEvent.change(roleInput, { target: { value: "Admin" } });

      const cancelButton = screen.getByText("Cancel");
      fireEvent.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  describe("Validation", () => {
    it("should show error when required fields are missing", async () => {
      renderModal();
      const submitButton = screen.getByText("Create Assignment");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockSetErrorData).toHaveBeenCalledWith({
          title: "Validation Error",
          list: ["User ID, Role, and Scope Type are required"],
        });
      });

      expect(API.api.post).not.toHaveBeenCalled();
    });

    it("should show error when scopeId is missing for non-Global scope", async () => {
      renderModal();

      fireEvent.change(screen.getByLabelText("User ID"), {
        target: { value: "user-123" },
      });
      fireEvent.change(screen.getByLabelText("Role"), {
        target: { value: "Admin" },
      });
      fireEvent.change(screen.getByLabelText("Scope Type"), {
        target: { value: "Project" },
      });

      const submitButton = screen.getByText("Create Assignment");
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

      fireEvent.change(screen.getByLabelText("User ID"), {
        target: { value: "user-123" },
      });
      fireEvent.change(screen.getByLabelText("Role"), {
        target: { value: "Admin" },
      });
      fireEvent.change(screen.getByLabelText("Scope Type"), {
        target: { value: "Global" },
      });
      fireEvent.change(screen.getByLabelText("Scope ID (optional)"), {
        target: { value: "should-be-empty" },
      });

      const submitButton = screen.getByText("Create Assignment");
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
    it("should call API with correct data on submit", async () => {
      (API.api.post as any).mockResolvedValueOnce({
        data: { id: "new-assignment-id" },
      });

      renderModal();

      fireEvent.change(screen.getByLabelText("User ID"), {
        target: { value: "user-123" },
      });
      fireEvent.change(screen.getByLabelText("Role"), {
        target: { value: "Admin" },
      });
      fireEvent.change(screen.getByLabelText("Scope Type"), {
        target: { value: "Project" },
      });
      fireEvent.change(screen.getByLabelText("Scope ID (optional)"), {
        target: { value: "project-456" },
      });

      const submitButton = screen.getByText("Create Assignment");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(API.api.post).toHaveBeenCalledWith("/api/v1/rbac/assignments", {
          user_id: "user-123",
          role_name: "Admin",
          scope_type: "Project",
          scope_id: "project-456",
        });
      });
    });

    it("should call API with null scope_id for Global scope", async () => {
      (API.api.post as any).mockResolvedValueOnce({
        data: { id: "new-assignment-id" },
      });

      renderModal();

      fireEvent.change(screen.getByLabelText("User ID"), {
        target: { value: "user-123" },
      });
      fireEvent.change(screen.getByLabelText("Role"), {
        target: { value: "Admin" },
      });
      fireEvent.change(screen.getByLabelText("Scope Type"), {
        target: { value: "Global" },
      });

      const submitButton = screen.getByText("Create Assignment");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(API.api.post).toHaveBeenCalledWith("/api/v1/rbac/assignments", {
          user_id: "user-123",
          role_name: "Admin",
          scope_type: "Global",
          scope_id: null,
        });
      });
    });

    it("should show success message on successful creation", async () => {
      (API.api.post as any).mockResolvedValueOnce({
        data: { id: "new-assignment-id" },
      });

      renderModal();

      fireEvent.change(screen.getByLabelText("User ID"), {
        target: { value: "user-123" },
      });
      fireEvent.change(screen.getByLabelText("Role"), {
        target: { value: "Admin" },
      });
      fireEvent.change(screen.getByLabelText("Scope Type"), {
        target: { value: "Global" },
      });

      const submitButton = screen.getByText("Create Assignment");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockSetSuccessData).toHaveBeenCalledWith({
          title: "Role assignment created successfully",
        });
      });
    });

    it("should call onSuccess callback on successful creation", async () => {
      (API.api.post as any).mockResolvedValueOnce({
        data: { id: "new-assignment-id" },
      });

      renderModal();

      fireEvent.change(screen.getByLabelText("User ID"), {
        target: { value: "user-123" },
      });
      fireEvent.change(screen.getByLabelText("Role"), {
        target: { value: "Admin" },
      });
      fireEvent.change(screen.getByLabelText("Scope Type"), {
        target: { value: "Global" },
      });

      const submitButton = screen.getByText("Create Assignment");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });

    it("should show error message on API failure", async () => {
      const errorMessage = "User not found";
      (API.api.post as any).mockRejectedValueOnce({
        response: { data: { detail: errorMessage } },
      });

      renderModal();

      fireEvent.change(screen.getByLabelText("User ID"), {
        target: { value: "invalid-user" },
      });
      fireEvent.change(screen.getByLabelText("Role"), {
        target: { value: "Admin" },
      });
      fireEvent.change(screen.getByLabelText("Scope Type"), {
        target: { value: "Global" },
      });

      const submitButton = screen.getByText("Create Assignment");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockSetErrorData).toHaveBeenCalledWith({
          title: "Failed to create role assignment",
          list: [errorMessage],
        });
      });
    });

    it("should show generic error message when API error has no detail", async () => {
      (API.api.post as any).mockRejectedValueOnce(new Error("Network error"));

      renderModal();

      fireEvent.change(screen.getByLabelText("User ID"), {
        target: { value: "user-123" },
      });
      fireEvent.change(screen.getByLabelText("Role"), {
        target: { value: "Admin" },
      });
      fireEvent.change(screen.getByLabelText("Scope Type"), {
        target: { value: "Global" },
      });

      const submitButton = screen.getByText("Create Assignment");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockSetErrorData).toHaveBeenCalledWith({
          title: "Failed to create role assignment",
          list: ["Network error"],
        });
      });
    });

    it("should disable buttons during submission", async () => {
      (API.api.post as any).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () => resolve({ data: { id: "new-assignment-id" } }),
              100,
            ),
          ),
      );

      renderModal();

      fireEvent.change(screen.getByLabelText("User ID"), {
        target: { value: "user-123" },
      });
      fireEvent.change(screen.getByLabelText("Role"), {
        target: { value: "Admin" },
      });
      fireEvent.change(screen.getByLabelText("Scope Type"), {
        target: { value: "Global" },
      });

      const submitButton = screen.getByText("Create Assignment");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
        expect(screen.getByText("Creating...")).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(mockSetSuccessData).toHaveBeenCalled();
      });
    });
  });

  describe("Query Cache Invalidation", () => {
    it("should invalidate assignments query on success", async () => {
      (API.api.post as any).mockResolvedValueOnce({
        data: { id: "new-assignment-id" },
      });

      const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");

      renderModal();

      fireEvent.change(screen.getByLabelText("User ID"), {
        target: { value: "user-123" },
      });
      fireEvent.change(screen.getByLabelText("Role"), {
        target: { value: "Admin" },
      });
      fireEvent.change(screen.getByLabelText("Scope Type"), {
        target: { value: "Global" },
      });

      const submitButton = screen.getByText("Create Assignment");
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(invalidateSpy).toHaveBeenCalledWith({
          queryKey: ["rbac-assignments"],
        });
      });
    });
  });
});
