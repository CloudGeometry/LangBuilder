import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { FlowType } from "@/types/flow";
import DropdownComponent from "../index";

// Mock the usePermission hook
jest.mock("@/hooks/usePermission", () => ({
  usePermission: jest.fn(),
}));

// Mock dependencies
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

jest.mock("../../../hooks/use-handle-duplicate", () => ({
  __esModule: true,
  default: () => ({
    handleDuplicate: jest.fn().mockResolvedValue({}),
  }),
}));

jest.mock("../../../hooks/use-select-options-change", () => ({
  __esModule: true,
  default: () => ({
    handleSelectOptionsChange: jest.fn(),
  }),
}));

jest.mock("@/components/common/genericIconComponent", () => ({
  __esModule: true,
  default: ({ name }: { name: string }) => (
    <span data-testid={`icon-${name}`}>{name}</span>
  ),
}));

import { usePermission } from "@/hooks/usePermission";

describe("DropdownComponent RBAC Integration", () => {
  let queryClient: QueryClient;

  const mockFlowData: FlowType = {
    id: "flow-123",
    name: "Test Flow",
    description: "Test description",
    data: { nodes: [], edges: [] },
    is_component: false,
    updated_at: new Date().toISOString(),
  };

  const mockSetOpenDelete = jest.fn();
  const mockHandleExport = jest.fn();
  const mockHandleEdit = jest.fn();

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DropdownMenu open>
          <DropdownMenuTrigger>Trigger</DropdownMenuTrigger>
          <DropdownMenuContent>{children}</DropdownMenuContent>
        </DropdownMenu>
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

  describe("Edit button permission guard", () => {
    it("should show Edit button when user has Update permission", async () => {
      // Mock usePermission to return different values based on permission type
      (usePermission as jest.Mock).mockImplementation(({ permission }) => {
        if (permission === "Update") {
          return {
            data: true, // User HAS Update permission
            isLoading: false,
            isSuccess: true,
          };
        }
        return {
          data: false,
          isLoading: false,
          isSuccess: true,
        };
      });

      render(
        <DropdownComponent
          flowData={mockFlowData}
          setOpenDelete={mockSetOpenDelete}
          handleExport={mockHandleExport}
          handleEdit={mockHandleEdit}
        />,
        { wrapper },
      );

      await waitFor(() => {
        expect(screen.getByTestId("btn-edit-flow")).toBeInTheDocument();
      });

      expect(screen.getByText("Edit details")).toBeInTheDocument();
    });

    it("should hide Edit button when user lacks Update permission", async () => {
      (usePermission as jest.Mock).mockImplementation(({ permission }) => {
        if (permission === "Update") {
          return {
            data: false, // User does NOT have Update permission
            isLoading: false,
            isSuccess: true,
          };
        }
        return {
          data: true,
          isLoading: false,
          isSuccess: true,
        };
      });

      render(
        <DropdownComponent
          flowData={mockFlowData}
          setOpenDelete={mockSetOpenDelete}
          handleExport={mockHandleExport}
          handleEdit={mockHandleEdit}
        />,
        { wrapper },
      );

      await waitFor(() => {
        // Wait for render to complete
        expect(screen.queryByTestId("btn-edit-flow")).not.toBeInTheDocument();
      });

      expect(screen.queryByText("Edit details")).not.toBeInTheDocument();
    });

    it("should check Update permission for the correct flow", async () => {
      const mockUsePermission = usePermission as jest.Mock;
      mockUsePermission.mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <DropdownComponent
          flowData={mockFlowData}
          setOpenDelete={mockSetOpenDelete}
          handleExport={mockHandleExport}
          handleEdit={mockHandleEdit}
        />,
        { wrapper },
      );

      await waitFor(() => {
        expect(mockUsePermission).toHaveBeenCalledWith(
          expect.objectContaining({
            permission: "Update",
            scope_type: "Flow",
            scope_id: "flow-123",
          }),
        );
      });
    });
  });

  describe("Delete button permission guard", () => {
    it("should show Delete button when user has Delete permission", async () => {
      (usePermission as jest.Mock).mockImplementation(({ permission }) => {
        if (permission === "Delete") {
          return {
            data: true, // User HAS Delete permission
            isLoading: false,
            isSuccess: true,
          };
        }
        return {
          data: false,
          isLoading: false,
          isSuccess: true,
        };
      });

      render(
        <DropdownComponent
          flowData={mockFlowData}
          setOpenDelete={mockSetOpenDelete}
          handleExport={mockHandleExport}
          handleEdit={mockHandleEdit}
        />,
        { wrapper },
      );

      await waitFor(() => {
        expect(
          screen.getByTestId("btn_delete_dropdown_menu"),
        ).toBeInTheDocument();
      });

      expect(screen.getByText("Delete")).toBeInTheDocument();
    });

    it("should hide Delete button when user lacks Delete permission", async () => {
      (usePermission as jest.Mock).mockImplementation(({ permission }) => {
        if (permission === "Delete") {
          return {
            data: false, // User does NOT have Delete permission
            isLoading: false,
            isSuccess: true,
          };
        }
        return {
          data: true,
          isLoading: false,
          isSuccess: true,
        };
      });

      render(
        <DropdownComponent
          flowData={mockFlowData}
          setOpenDelete={mockSetOpenDelete}
          handleExport={mockHandleExport}
          handleEdit={mockHandleEdit}
        />,
        { wrapper },
      );

      await waitFor(() => {
        expect(
          screen.queryByTestId("btn_delete_dropdown_menu"),
        ).not.toBeInTheDocument();
      });

      expect(screen.queryByText("Delete")).not.toBeInTheDocument();
    });

    it("should check Delete permission for the correct flow", async () => {
      const mockUsePermission = usePermission as jest.Mock;
      mockUsePermission.mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <DropdownComponent
          flowData={mockFlowData}
          setOpenDelete={mockSetOpenDelete}
          handleExport={mockHandleExport}
          handleEdit={mockHandleEdit}
        />,
        { wrapper },
      );

      await waitFor(() => {
        expect(mockUsePermission).toHaveBeenCalledWith(
          expect.objectContaining({
            permission: "Delete",
            scope_type: "Flow",
            scope_id: "flow-123",
          }),
        );
      });
    });
  });

  describe("Unrestricted menu items", () => {
    it("should always show Export button regardless of permissions", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false, // User has NO permissions
        isLoading: false,
        isSuccess: true,
      });

      render(
        <DropdownComponent
          flowData={mockFlowData}
          setOpenDelete={mockSetOpenDelete}
          handleExport={mockHandleExport}
          handleEdit={mockHandleEdit}
        />,
        { wrapper },
      );

      await waitFor(() => {
        expect(screen.getByTestId("btn-download-json")).toBeInTheDocument();
      });

      expect(screen.getByText("Export")).toBeInTheDocument();
    });

    it("should always show Duplicate button regardless of permissions", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false, // User has NO permissions
        isLoading: false,
        isSuccess: true,
      });

      render(
        <DropdownComponent
          flowData={mockFlowData}
          setOpenDelete={mockSetOpenDelete}
          handleExport={mockHandleExport}
          handleEdit={mockHandleEdit}
        />,
        { wrapper },
      );

      await waitFor(() => {
        expect(screen.getByTestId("btn-duplicate-flow")).toBeInTheDocument();
      });

      expect(screen.getByText("Duplicate")).toBeInTheDocument();
    });
  });

  describe("Combined permission scenarios", () => {
    it("should show Edit and Delete when user has both permissions", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true, // User has ALL permissions
        isLoading: false,
        isSuccess: true,
      });

      render(
        <DropdownComponent
          flowData={mockFlowData}
          setOpenDelete={mockSetOpenDelete}
          handleExport={mockHandleExport}
          handleEdit={mockHandleEdit}
        />,
        { wrapper },
      );

      await waitFor(() => {
        expect(screen.getByTestId("btn-edit-flow")).toBeInTheDocument();
        expect(
          screen.getByTestId("btn_delete_dropdown_menu"),
        ).toBeInTheDocument();
      });

      // All 4 menu items should be visible
      expect(screen.getByText("Edit details")).toBeInTheDocument();
      expect(screen.getByText("Export")).toBeInTheDocument();
      expect(screen.getByText("Duplicate")).toBeInTheDocument();
      expect(screen.getByText("Delete")).toBeInTheDocument();
    });

    it("should hide Edit and Delete when user has no permissions", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false, // User has NO permissions
        isLoading: false,
        isSuccess: true,
      });

      render(
        <DropdownComponent
          flowData={mockFlowData}
          setOpenDelete={mockSetOpenDelete}
          handleExport={mockHandleExport}
          handleEdit={mockHandleEdit}
        />,
        { wrapper },
      );

      await waitFor(() => {
        // Only Export and Duplicate should be visible
        expect(screen.getByTestId("btn-download-json")).toBeInTheDocument();
        expect(screen.getByTestId("btn-duplicate-flow")).toBeInTheDocument();
      });

      expect(screen.queryByTestId("btn-edit-flow")).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("btn_delete_dropdown_menu"),
      ).not.toBeInTheDocument();
      expect(screen.queryByText("Edit details")).not.toBeInTheDocument();
      expect(screen.queryByText("Delete")).not.toBeInTheDocument();
    });

    it("should show only Edit when user has Update but not Delete permission", async () => {
      (usePermission as jest.Mock).mockImplementation(({ permission }) => {
        return {
          data: permission === "Update", // Only Update permission
          isLoading: false,
          isSuccess: true,
        };
      });

      render(
        <DropdownComponent
          flowData={mockFlowData}
          setOpenDelete={mockSetOpenDelete}
          handleExport={mockHandleExport}
          handleEdit={mockHandleEdit}
        />,
        { wrapper },
      );

      await waitFor(() => {
        expect(screen.getByTestId("btn-edit-flow")).toBeInTheDocument();
      });

      expect(screen.getByText("Edit details")).toBeInTheDocument();
      expect(screen.queryByText("Delete")).not.toBeInTheDocument();
    });

    it("should show only Delete when user has Delete but not Update permission", async () => {
      (usePermission as jest.Mock).mockImplementation(({ permission }) => {
        return {
          data: permission === "Delete", // Only Delete permission
          isLoading: false,
          isSuccess: true,
        };
      });

      render(
        <DropdownComponent
          flowData={mockFlowData}
          setOpenDelete={mockSetOpenDelete}
          handleExport={mockHandleExport}
          handleEdit={mockHandleEdit}
        />,
        { wrapper },
      );

      await waitFor(() => {
        expect(
          screen.getByTestId("btn_delete_dropdown_menu"),
        ).toBeInTheDocument();
      });

      expect(screen.getByText("Delete")).toBeInTheDocument();
      expect(screen.queryByText("Edit details")).not.toBeInTheDocument();
    });
  });

  describe("RBACGuard integration", () => {
    it("should use separate RBACGuard instances for Edit and Delete", async () => {
      const mockUsePermission = usePermission as jest.Mock;
      mockUsePermission.mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <DropdownComponent
          flowData={mockFlowData}
          setOpenDelete={mockSetOpenDelete}
          handleExport={mockHandleExport}
          handleEdit={mockHandleEdit}
        />,
        { wrapper },
      );

      await waitFor(() => {
        // Should make separate permission checks for Update and Delete
        expect(mockUsePermission).toHaveBeenCalledWith({
          permission: "Update",
          scope_type: "Flow",
          scope_id: "flow-123",
        });

        expect(mockUsePermission).toHaveBeenCalledWith({
          permission: "Delete",
          scope_type: "Flow",
          scope_id: "flow-123",
        });
      });
    });
  });
});
