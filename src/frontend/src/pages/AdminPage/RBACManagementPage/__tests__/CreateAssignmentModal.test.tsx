import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import * as API from "@/controllers/API";
import useAlertStore from "@/stores/alertStore";
import CreateAssignmentModal from "../CreateAssignmentModal";

// Mock API
jest.mock("@/controllers/API", () => ({
  api: {
    get: jest.fn(),
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

// Mock CustomLoader
jest.mock("@/customization/components/custom-loader", () => ({
  __esModule: true,
  default: () => <div>Loading...</div>,
}));

// Mock lucide-react icons
jest.mock("lucide-react", () => ({
  Check: () => <span>✓</span>,
  ChevronDown: () => <span>▼</span>,
  ChevronUp: () => <span>▲</span>,
  X: () => <span>✕</span>,
  Search: () => <span>🔍</span>,
  CircleIcon: () => <span>○</span>,
}));

describe("CreateAssignmentModal", () => {
  let queryClient: QueryClient;
  let mockOnClose: jest.Mock;
  let mockOnSuccess: jest.Mock;

  const mockUsers = [
    { id: "user-1", username: "alice" },
    { id: "user-2", username: "bob" },
  ];

  const mockFolders = [
    { id: "folder-1", name: "Project Alpha" },
    { id: "folder-2", name: "Project Beta" },
  ];

  const mockFlows = [
    { id: "flow-1", name: "Flow One" },
    { id: "flow-2", name: "Flow Two" },
  ];

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

    // Setup default API mocks
    (API.api.get as jest.Mock).mockImplementation((url: string) => {
      if (url === "/api/v1/users") {
        return Promise.resolve({ data: mockUsers });
      }
      if (url === "/api/v1/folders") {
        return Promise.resolve({ data: mockFolders });
      }
      if (url === "/api/v1/flows") {
        return Promise.resolve({ data: mockFlows });
      }
      return Promise.reject(new Error("Unknown endpoint"));
    });
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
    it("should render modal when open", async () => {
      renderModal();
      await waitFor(() => {
        expect(screen.getByText("Create Role Assignment")).toBeInTheDocument();
      });
    });

    it("should not render modal when closed", () => {
      renderModal(false);
      expect(
        screen.queryByText("Create Role Assignment"),
      ).not.toBeInTheDocument();
    });

    it("should show step 1 by default", async () => {
      renderModal();
      await waitFor(() => {
        expect(screen.getByText(/Step 1 of/)).toBeInTheDocument();
        expect(screen.getByText(/Select User/)).toBeInTheDocument();
      });
    });

    it("should render navigation buttons", async () => {
      renderModal();
      await waitFor(() => {
        expect(screen.getByText("Back")).toBeInTheDocument();
        expect(screen.getByText("Next")).toBeInTheDocument();
      });
    });
  });

  describe("Step 1: User Selection", () => {
    it("should load and display users", async () => {
      renderModal();
      await waitFor(() => {
        expect(API.api.get).toHaveBeenCalledWith("/api/v1/users");
      });

      // Find select by id and open the dropdown
      const selectTrigger = screen.getByRole("combobox");
      fireEvent.click(selectTrigger);

      await waitFor(() => {
        expect(screen.getByText("alice")).toBeInTheDocument();
        expect(screen.getByText("bob")).toBeInTheDocument();
      });
    });

    it("should show loading state while fetching users", async () => {
      (API.api.get as jest.Mock).mockImplementation(
        (url: string) =>
          new Promise((resolve) => {
            if (url === "/api/v1/users") {
              setTimeout(() => resolve({ data: mockUsers }), 100);
            }
          }),
      );

      renderModal();
      expect(screen.getByText("Loading...")).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.queryByText("Loading...")).not.toBeInTheDocument();
      });
    });

    it("should disable Next button when no user is selected", async () => {
      renderModal();
      await waitFor(() => {
        const nextButton = screen.getByText("Next");
        expect(nextButton).toBeDisabled();
      });
    });

    it("should enable Next button when user is selected", async () => {
      renderModal();
      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      const selectTrigger = screen.getByRole("combobox", { name: /user/i });
      fireEvent.click(selectTrigger);

      await waitFor(() => {
        const aliceOption = screen.getByText("alice");
        fireEvent.click(aliceOption);
      });

      await waitFor(() => {
        const nextButton = screen.getByText("Next");
        expect(nextButton).not.toBeDisabled();
      });
    });

    it("should disable Back button on first step", async () => {
      renderModal();
      await waitFor(() => {
        const backButton = screen.getByText("Back");
        expect(backButton).toBeDisabled();
      });
    });
  });

  describe("Step 2: Scope Type Selection", () => {
    const navigateToStep2 = async () => {
      renderModal();
      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      const selectTrigger = screen.getByRole("combobox", { name: /user/i });
      fireEvent.click(selectTrigger);

      await waitFor(() => {
        const aliceOption = screen.getByText("alice");
        fireEvent.click(aliceOption);
      });

      const nextButton = screen.getByText("Next");
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText(/Step 2 of/)).toBeInTheDocument();
      });
    };

    it("should navigate to step 2 after selecting user", async () => {
      await navigateToStep2();
      expect(screen.getByText(/Select Scope Type/)).toBeInTheDocument();
    });

    it("should show scope type options", async () => {
      await navigateToStep2();

      const scopeSelect = screen.getByRole("combobox", {
        name: /scope type/i,
      });
      fireEvent.click(scopeSelect);

      await waitFor(() => {
        expect(screen.getByText("Global (Admin only)")).toBeInTheDocument();
        expect(screen.getByText("Project")).toBeInTheDocument();
        expect(screen.getByText("Flow")).toBeInTheDocument();
      });
    });

    it("should disable Next button when no scope type is selected", async () => {
      await navigateToStep2();
      const nextButton = screen.getByText("Next");
      expect(nextButton).toBeDisabled();
    });

    it("should enable Back button on step 2", async () => {
      await navigateToStep2();
      const backButton = screen.getByText("Back");
      expect(backButton).not.toBeDisabled();
    });
  });

  describe("Step 3: Resource Selection (Project/Flow)", () => {
    const navigateToStep3WithProject = async () => {
      renderModal();
      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      // Select user
      const userSelect = screen.getByRole("combobox", { name: /user/i });
      fireEvent.click(userSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("alice"));
      });
      fireEvent.click(screen.getByText("Next"));

      // Select scope type
      await waitFor(() => {
        expect(screen.getByText(/Step 2 of/)).toBeInTheDocument();
      });
      const scopeSelect = screen.getByRole("combobox", {
        name: /scope type/i,
      });
      fireEvent.click(scopeSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("Project"));
      });
      fireEvent.click(screen.getByText("Next"));

      await waitFor(() => {
        expect(screen.getByText(/Step 3 of/)).toBeInTheDocument();
      });
    };

    const navigateToStep3WithFlow = async () => {
      renderModal();
      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      // Select user
      const userSelect = screen.getByRole("combobox", { name: /user/i });
      fireEvent.click(userSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("alice"));
      });
      fireEvent.click(screen.getByText("Next"));

      // Select scope type
      await waitFor(() => {
        expect(screen.getByText(/Step 2 of/)).toBeInTheDocument();
      });
      const scopeSelect = screen.getByRole("combobox", {
        name: /scope type/i,
      });
      fireEvent.click(scopeSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("Flow"));
      });
      fireEvent.click(screen.getByText("Next"));

      await waitFor(() => {
        expect(screen.getByText(/Step 3 of/)).toBeInTheDocument();
      });
    };

    it("should load and display projects when Project scope is selected", async () => {
      await navigateToStep3WithProject();

      await waitFor(() => {
        expect(API.api.get).toHaveBeenCalledWith("/api/v1/folders");
      });

      const resourceSelect = screen.getByRole("combobox", {
        name: /project/i,
      });
      fireEvent.click(resourceSelect);

      await waitFor(() => {
        expect(screen.getByText("Project Alpha")).toBeInTheDocument();
        expect(screen.getByText("Project Beta")).toBeInTheDocument();
      });
    });

    it("should load and display flows when Flow scope is selected", async () => {
      await navigateToStep3WithFlow();

      await waitFor(() => {
        expect(API.api.get).toHaveBeenCalledWith("/api/v1/flows");
      });

      const resourceSelect = screen.getByRole("combobox", { name: /flow/i });
      fireEvent.click(resourceSelect);

      await waitFor(() => {
        expect(screen.getByText("Flow One")).toBeInTheDocument();
        expect(screen.getByText("Flow Two")).toBeInTheDocument();
      });
    });

    it("should disable Next button when no resource is selected", async () => {
      await navigateToStep3WithProject();
      const nextButton = screen.getByText("Next");
      expect(nextButton).toBeDisabled();
    });
  });

  describe("Step 3/4: Global Scope - Skip Resource Selection", () => {
    const navigateToStep4WithGlobal = async () => {
      renderModal();
      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      // Select user
      const userSelect = screen.getByRole("combobox", { name: /user/i });
      fireEvent.click(userSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("alice"));
      });
      fireEvent.click(screen.getByText("Next"));

      // Select Global scope type
      await waitFor(() => {
        expect(screen.getByText(/Step 2 of/)).toBeInTheDocument();
      });
      const scopeSelect = screen.getByRole("combobox", {
        name: /scope type/i,
      });
      fireEvent.click(scopeSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("Global (Admin only)"));
      });
      fireEvent.click(screen.getByText("Next"));

      await waitFor(() => {
        expect(screen.getByText(/Step 3 of 3/)).toBeInTheDocument();
      });
    };

    it("should skip step 3 for Global scope", async () => {
      await navigateToStep4WithGlobal();
      expect(screen.getByText(/Select Role/)).toBeInTheDocument();
      expect(screen.getByText(/Step 3 of 3/)).toBeInTheDocument();
    });

    it("should show only Admin role for Global scope", async () => {
      await navigateToStep4WithGlobal();

      const roleSelect = screen.getByRole("combobox", { name: /role/i });
      fireEvent.click(roleSelect);

      await waitFor(() => {
        expect(screen.getByText("Admin")).toBeInTheDocument();
        expect(screen.queryByText("Owner")).not.toBeInTheDocument();
        expect(screen.queryByText("Editor")).not.toBeInTheDocument();
        expect(screen.queryByText("Viewer")).not.toBeInTheDocument();
      });
    });

    it("should show Create Assignment button on final step", async () => {
      await navigateToStep4WithGlobal();
      expect(screen.getByText("Create Assignment")).toBeInTheDocument();
    });
  });

  describe("Step 4: Role Selection (Project/Flow)", () => {
    const navigateToStep4WithProject = async () => {
      renderModal();
      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      // Select user
      const userSelect = screen.getByRole("combobox", { name: /user/i });
      fireEvent.click(userSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("alice"));
      });
      fireEvent.click(screen.getByText("Next"));

      // Select scope type
      await waitFor(() => {
        expect(screen.getByText(/Step 2 of/)).toBeInTheDocument();
      });
      const scopeSelect = screen.getByRole("combobox", {
        name: /scope type/i,
      });
      fireEvent.click(scopeSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("Project"));
      });
      fireEvent.click(screen.getByText("Next"));

      // Select project
      await waitFor(() => {
        expect(screen.getByText(/Step 3 of/)).toBeInTheDocument();
      });
      const projectSelect = screen.getByRole("combobox", {
        name: /project/i,
      });
      fireEvent.click(projectSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("Project Alpha"));
      });
      fireEvent.click(screen.getByText("Next"));

      await waitFor(() => {
        expect(screen.getByText(/Step 4 of 4/)).toBeInTheDocument();
      });
    };

    it("should show Owner, Editor, Viewer roles for Project scope", async () => {
      await navigateToStep4WithProject();

      const roleSelect = screen.getByRole("combobox", { name: /role/i });
      fireEvent.click(roleSelect);

      await waitFor(() => {
        expect(screen.getByText("Owner")).toBeInTheDocument();
        expect(screen.getByText("Editor")).toBeInTheDocument();
        expect(screen.getByText("Viewer")).toBeInTheDocument();
        expect(screen.queryByText("Admin")).not.toBeInTheDocument();
      });
    });
  });

  describe("Navigation", () => {
    it("should navigate back from step 2 to step 1", async () => {
      renderModal();
      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      // Navigate to step 2
      const userSelect = screen.getByRole("combobox", { name: /user/i });
      fireEvent.click(userSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("alice"));
      });
      fireEvent.click(screen.getByText("Next"));

      await waitFor(() => {
        expect(screen.getByText(/Step 2 of/)).toBeInTheDocument();
      });

      // Navigate back to step 1
      fireEvent.click(screen.getByText("Back"));

      await waitFor(() => {
        expect(screen.getByText(/Step 1 of/)).toBeInTheDocument();
        expect(screen.getByText(/Select User/)).toBeInTheDocument();
      });
    });

    it("should navigate back from step 4 to step 2 for Global scope", async () => {
      renderModal();
      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      // Navigate to Global role selection
      const userSelect = screen.getByRole("combobox", { name: /user/i });
      fireEvent.click(userSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("alice"));
      });
      fireEvent.click(screen.getByText("Next"));

      await waitFor(() => {
        expect(screen.getByText(/Step 2 of/)).toBeInTheDocument();
      });

      const scopeSelect = screen.getByRole("combobox", {
        name: /scope type/i,
      });
      fireEvent.click(scopeSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("Global (Admin only)"));
      });
      fireEvent.click(screen.getByText("Next"));

      await waitFor(() => {
        expect(screen.getByText(/Step 3 of 3/)).toBeInTheDocument();
      });

      // Navigate back - should skip step 3 and go to step 2
      fireEvent.click(screen.getByText("Back"));

      await waitFor(() => {
        expect(screen.getByText(/Step 2 of/)).toBeInTheDocument();
      });
    });

    it("should reset form when modal is closed", async () => {
      renderModal();
      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      // Select user and navigate
      const userSelect = screen.getByRole("combobox", { name: /user/i });
      fireEvent.click(userSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("alice"));
      });

      // Close modal
      fireEvent.click(screen.getByText("Back"));
      expect(mockOnClose).not.toHaveBeenCalled();

      // Try to close by clicking outside or close button
      const dialog = screen.getByRole("dialog");
      fireEvent.keyDown(dialog, { key: "Escape" });

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalled();
      });
    });
  });

  describe("API Integration", () => {
    const completeWorkflowWithGlobal = async () => {
      renderModal();
      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      // Step 1: Select user
      const userSelect = screen.getByRole("combobox", { name: /user/i });
      fireEvent.click(userSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("alice"));
      });
      fireEvent.click(screen.getByText("Next"));

      // Step 2: Select scope
      await waitFor(() => {
        expect(screen.getByText(/Step 2 of/)).toBeInTheDocument();
      });
      const scopeSelect = screen.getByRole("combobox", {
        name: /scope type/i,
      });
      fireEvent.click(scopeSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("Global (Admin only)"));
      });
      fireEvent.click(screen.getByText("Next"));

      // Step 3/4: Select role
      await waitFor(() => {
        expect(screen.getByText(/Step 3 of 3/)).toBeInTheDocument();
      });
      const roleSelect = screen.getByRole("combobox", { name: /role/i });
      fireEvent.click(roleSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("Admin"));
      });
    };

    it("should call API with correct data for Global scope", async () => {
      (API.api.post as jest.Mock).mockResolvedValueOnce({
        data: { id: "assignment-1" },
      });

      await completeWorkflowWithGlobal();

      const createButton = screen.getByText("Create Assignment");
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(API.api.post).toHaveBeenCalledWith("/api/v1/rbac/assignments", {
          user_id: "user-1",
          role_name: "Admin",
          scope_type: "Global",
          scope_id: null,
        });
      });
    });

    it("should call API with correct data for Project scope", async () => {
      (API.api.post as jest.Mock).mockResolvedValueOnce({
        data: { id: "assignment-1" },
      });

      renderModal();
      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      // Complete workflow with Project
      const userSelect = screen.getByRole("combobox", { name: /user/i });
      fireEvent.click(userSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("alice"));
      });
      fireEvent.click(screen.getByText("Next"));

      await waitFor(() => {
        expect(screen.getByText(/Step 2 of/)).toBeInTheDocument();
      });
      const scopeSelect = screen.getByRole("combobox", {
        name: /scope type/i,
      });
      fireEvent.click(scopeSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("Project"));
      });
      fireEvent.click(screen.getByText("Next"));

      await waitFor(() => {
        expect(screen.getByText(/Step 3 of/)).toBeInTheDocument();
      });
      const projectSelect = screen.getByRole("combobox", {
        name: /project/i,
      });
      fireEvent.click(projectSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("Project Alpha"));
      });
      fireEvent.click(screen.getByText("Next"));

      await waitFor(() => {
        expect(screen.getByText(/Step 4 of 4/)).toBeInTheDocument();
      });
      const roleSelect = screen.getByRole("combobox", { name: /role/i });
      fireEvent.click(roleSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("Owner"));
      });

      const createButton = screen.getByText("Create Assignment");
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(API.api.post).toHaveBeenCalledWith("/api/v1/rbac/assignments", {
          user_id: "user-1",
          role_name: "Owner",
          scope_type: "Project",
          scope_id: "folder-1",
        });
      });
    });

    it("should show success message on successful creation", async () => {
      (API.api.post as jest.Mock).mockResolvedValueOnce({
        data: { id: "assignment-1" },
      });

      await completeWorkflowWithGlobal();

      const createButton = screen.getByText("Create Assignment");
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(mockSetSuccessData).toHaveBeenCalledWith({
          title: "Role assignment created successfully",
        });
      });
    });

    it("should call onSuccess callback on successful creation", async () => {
      (API.api.post as jest.Mock).mockResolvedValueOnce({
        data: { id: "assignment-1" },
      });

      await completeWorkflowWithGlobal();

      const createButton = screen.getByText("Create Assignment");
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });

    it("should show error message on API failure", async () => {
      const errorMessage = "User not found";
      (API.api.post as jest.Mock).mockRejectedValueOnce({
        response: { data: { detail: errorMessage } },
      });

      await completeWorkflowWithGlobal();

      const createButton = screen.getByText("Create Assignment");
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(mockSetErrorData).toHaveBeenCalledWith({
          title: "Failed to create role assignment",
          list: [errorMessage],
        });
      });
    });

    it("should show generic error message when API error has no detail", async () => {
      (API.api.post as jest.Mock).mockRejectedValueOnce(
        new Error("Network error"),
      );

      await completeWorkflowWithGlobal();

      const createButton = screen.getByText("Create Assignment");
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(mockSetErrorData).toHaveBeenCalledWith({
          title: "Failed to create role assignment",
          list: ["Network error"],
        });
      });
    });

    it("should disable buttons during submission", async () => {
      let resolvePromise: (value: any) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      (API.api.post as jest.Mock).mockImplementation(() => pendingPromise);

      await completeWorkflowWithGlobal();

      const createButton = screen.getByText("Create Assignment");
      fireEvent.click(createButton);

      // Check that button is disabled during submission
      await waitFor(() => {
        expect(screen.getByText("Creating...")).toBeInTheDocument();
      });

      // Resolve the promise
      resolvePromise!({ data: { id: "assignment-1" } });

      await waitFor(() => {
        expect(mockSetSuccessData).toHaveBeenCalled();
      });
    });
  });

  describe("Query Cache Invalidation", () => {
    it("should invalidate assignments query on success", async () => {
      (API.api.post as jest.Mock).mockResolvedValueOnce({
        data: { id: "assignment-1" },
      });

      const invalidateSpy = jest.spyOn(queryClient, "invalidateQueries");

      renderModal();
      await waitFor(() => {
        expect(screen.getByRole("combobox")).toBeInTheDocument();
      });

      // Complete workflow
      const userSelect = screen.getByRole("combobox", { name: /user/i });
      fireEvent.click(userSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("alice"));
      });
      fireEvent.click(screen.getByText("Next"));

      await waitFor(() => {
        expect(screen.getByText(/Step 2 of/)).toBeInTheDocument();
      });
      const scopeSelect = screen.getByRole("combobox", {
        name: /scope type/i,
      });
      fireEvent.click(scopeSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("Global (Admin only)"));
      });
      fireEvent.click(screen.getByText("Next"));

      await waitFor(() => {
        expect(screen.getByText(/Step 3 of 3/)).toBeInTheDocument();
      });
      const roleSelect = screen.getByRole("combobox", { name: /role/i });
      fireEvent.click(roleSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText("Admin"));
      });

      const createButton = screen.getByText("Create Assignment");
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(invalidateSpy).toHaveBeenCalledWith({
          queryKey: ["rbac-assignments"],
        });
      });
    });
  });
});
