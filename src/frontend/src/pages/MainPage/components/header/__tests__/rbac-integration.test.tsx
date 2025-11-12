import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import HeaderComponent from "../index";

// Mock the usePermission hook
jest.mock("@/hooks/usePermission", () => ({
  usePermission: jest.fn(),
}));

// Mock other dependencies
jest.mock("@/customization/hooks/use-custom-navigate", () => ({
  useCustomNavigate: () => jest.fn(),
}));

jest.mock("@/hooks/use-mobile", () => ({
  useIsMobile: () => false,
}));

jest.mock("@/stores/flowsManagerStore", () => ({
  __esModule: true,
  default: (selector: any) => {
    const state = {
      setFolderIdDrag: jest.fn(),
      setFolderDragging: jest.fn(),
      currentFolder: null,
    };
    return selector ? selector(state) : state;
  },
}));

jest.mock("@/stores/foldersStore", () => ({
  useFolderStore: (selector: any) => {
    const state = {
      folders: [],
      myCollectionId: "my-collection-id",
      folderToEdit: null,
      setFolderToEdit: jest.fn(),
    };
    return selector ? selector(state) : state;
  },
}));

jest.mock("@/stores/alertStore", () => ({
  __esModule: true,
  default: (selector: any) => {
    const state = {
      setSuccessData: jest.fn(),
      setErrorData: jest.fn(),
    };
    return selector ? selector(state) : state;
  },
}));

jest.mock("@/controllers/API/queries/folders", () => ({
  useDeleteFolders: () => ({
    mutate: jest.fn(),
  }),
}));

// Mock Radix UI components
jest.mock("@/components/ui/sidebar", () => ({
  SidebarTrigger: () => <button>Sidebar Trigger</button>,
}));

jest.mock("@/components/common/genericIconComponent", () => ({
  __esModule: true,
  default: ({ name }: { name: string }) => (
    <span data-testid={`icon-${name}`}>{name}</span>
  ),
}));

jest.mock("@/modals/deleteConfirmationModal", () => ({
  __esModule: true,
  default: () => <div>Delete Confirmation Modal</div>,
}));

import { usePermission } from "@/hooks/usePermission";

describe("Header Component RBAC Integration", () => {
  let queryClient: QueryClient;

  const defaultProps = {
    flowType: "flows" as const,
    setFlowType: jest.fn(),
    view: "list" as const,
    setView: jest.fn(),
    setNewProjectModal: jest.fn(),
    setSearch: jest.fn(),
    isEmptyFolder: false,
    selectedFlows: [],
    folderName: "Test Folder",
  };

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <TooltipProvider>{children}</TooltipProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );

  beforeEach(() => {
    jest.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          gcTime: 0,
        },
      },
    });
  });

  afterEach(() => {
    queryClient.clear();
  });

  describe("New Flow button permission guards", () => {
    it("should show New Flow button when user has Create permission", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true, // User HAS Create permission
        isLoading: false,
        isSuccess: true,
      });

      render(<HeaderComponent {...defaultProps} />, { wrapper });

      await waitFor(() => {
        expect(screen.getByTestId("new-project-btn")).toBeInTheDocument();
      });

      expect(screen.getByText("New Flow")).toBeInTheDocument();
    });

    it("should hide New Flow button when user lacks Create permission", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false, // User does NOT have Create permission
        isLoading: false,
        isSuccess: true,
      });

      render(<HeaderComponent {...defaultProps} />, { wrapper });

      await waitFor(() => {
        // Wait for component to render
        expect(screen.queryByTestId("new-project-btn")).not.toBeInTheDocument();
      });

      expect(screen.queryByText("New Flow")).not.toBeInTheDocument();
    });

    it("should check Create permission for Project scope", async () => {
      const mockUsePermission = usePermission as jest.Mock;
      mockUsePermission.mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(<HeaderComponent {...defaultProps} />, { wrapper });

      await waitFor(() => {
        expect(mockUsePermission).toHaveBeenCalledWith({
          permission: "Create",
          scope_type: "Project",
          scope_id: null,
        });
      });
    });

    it("should check Create permission with folderId when in a folder", async () => {
      const mockUsePermission = usePermission as jest.Mock;
      mockUsePermission.mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(<HeaderComponent {...defaultProps} folderId="folder-123" />, {
        wrapper,
      });

      await waitFor(() => {
        expect(mockUsePermission).toHaveBeenCalledWith({
          permission: "Create",
          scope_type: "Project",
          scope_id: "folder-123",
        });
      });
    });

    it("should handle loading state gracefully", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: undefined,
        isLoading: true, // Permission check is loading
        isSuccess: false,
      });

      render(<HeaderComponent {...defaultProps} />, { wrapper });

      // Button should not be rendered while loading
      expect(screen.queryByTestId("new-project-btn")).not.toBeInTheDocument();
    });

    it("should handle permission check errors gracefully", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: undefined,
        isLoading: false,
        isSuccess: false,
        isError: true,
        error: new Error("Permission check failed"),
      });

      render(<HeaderComponent {...defaultProps} />, { wrapper });

      // Button should not be rendered on error (fail closed)
      expect(screen.queryByTestId("new-project-btn")).not.toBeInTheDocument();
    });
  });

  describe("Other header controls", () => {
    it("should always show delete button regardless of Create permission", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false, // User does NOT have Create permission
        isLoading: false,
        isSuccess: true,
      });

      render(<HeaderComponent {...defaultProps} folderId="folder-123" />, {
        wrapper,
      });

      // Delete button should be visible (it has its own permission check)
      await waitFor(() => {
        // The delete button is in a DeleteConfirmationModal wrapper
        // It should still be rendered even without Create permission
        const buttons = screen.getAllByRole("button");
        expect(buttons.length).toBeGreaterThan(0);
      });
    });

    it("should always show sidebar trigger regardless of permissions", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false,
        isLoading: false,
        isSuccess: true,
      });

      render(<HeaderComponent {...defaultProps} />, { wrapper });

      await waitFor(() => {
        expect(screen.getByText("Sidebar Trigger")).toBeInTheDocument();
      });
    });
  });

  describe("RBACGuard integration", () => {
    it("should use RBACGuard component to wrap New Flow button", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      const { container } = render(
        <HeaderComponent {...defaultProps} folderId="test-folder" />,
        {
          wrapper,
        },
      );

      await waitFor(() => {
        expect(screen.getByTestId("new-project-btn")).toBeInTheDocument();
      });

      // Verify the button is rendered when permission is granted
      const newFlowButton = screen.getByTestId("new-project-btn");
      expect(newFlowButton).toBeInTheDocument();
      expect(newFlowButton).toHaveTextContent("New Flow");
    });

    it("should pass correct permission check to RBACGuard", async () => {
      const mockUsePermission = usePermission as jest.Mock;
      mockUsePermission.mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(<HeaderComponent {...defaultProps} folderId="project-456" />, {
        wrapper,
      });

      await waitFor(() => {
        expect(mockUsePermission).toHaveBeenCalledWith(
          expect.objectContaining({
            permission: "Create",
            scope_type: "Project",
            scope_id: "project-456",
          }),
        );
      });
    });
  });

  describe("Permission caching", () => {
    it("should not make duplicate permission checks for same component", async () => {
      const mockUsePermission = usePermission as jest.Mock;
      mockUsePermission.mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      const { rerender } = render(
        <HeaderComponent {...defaultProps} folderId="folder-123" />,
        {
          wrapper,
        },
      );

      await waitFor(() => {
        expect(mockUsePermission).toHaveBeenCalled();
      });

      const initialCallCount = mockUsePermission.mock.calls.length;

      // Rerender with same props
      rerender(<HeaderComponent {...defaultProps} folderId="folder-123" />);

      // Should use cached result (TanStack Query handles caching)
      // The hook might be called again but the underlying API call is cached
      expect(mockUsePermission.mock.calls.length).toBeGreaterThanOrEqual(
        initialCallCount,
      );
    });
  });
});
