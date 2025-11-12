import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { ReactNode } from "react";
import { api } from "@/controllers/API";
import RBACGuard from "../index";

// Mock the API
jest.mock("@/controllers/API", () => ({
  api: {
    get: jest.fn(),
  },
}));

// Mock the usePermission hook
jest.mock("@/hooks/usePermission", () => ({
  usePermission: jest.fn(),
  PermissionCheck: {},
}));

import { usePermission } from "@/hooks/usePermission";

describe("RBACGuard", () => {
  let queryClient: QueryClient;

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
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

  describe("Permission granted scenarios", () => {
    it("should render children when user has permission", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <RBACGuard
          check={{
            permission: "Delete",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
        >
          <button>Delete Flow</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.getByText("Delete Flow")).toBeInTheDocument();
    });

    it("should render children with complex content when permission is granted", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <RBACGuard
          check={{
            permission: "Update",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
        >
          <div>
            <h1>Edit Flow</h1>
            <button>Save</button>
            <button>Cancel</button>
          </div>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.getByText("Edit Flow")).toBeInTheDocument();
      expect(screen.getByText("Save")).toBeInTheDocument();
      expect(screen.getByText("Cancel")).toBeInTheDocument();
    });
  });

  describe("Permission denied scenarios", () => {
    it("should hide children by default when user lacks permission", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <RBACGuard
          check={{
            permission: "Delete",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
        >
          <button>Delete Flow</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.queryByText("Delete Flow")).not.toBeInTheDocument();
    });

    it("should render fallback when hideWhenDenied is false and user lacks permission", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <RBACGuard
          check={{
            permission: "Update",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
          fallback={<button disabled>Save (Read-only)</button>}
          hideWhenDenied={false}
        >
          <button>Save</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.queryByText("Save")).not.toBeInTheDocument();
      expect(screen.getByText("Save (Read-only)")).toBeInTheDocument();
      expect(screen.getByText("Save (Read-only)")).toBeDisabled();
    });

    it("should render null when fallback is not provided and hideWhenDenied is false", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false,
        isLoading: false,
        isSuccess: true,
      });

      const { container } = render(
        <RBACGuard
          check={{
            permission: "Delete",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
          hideWhenDenied={false}
        >
          <button>Delete Flow</button>
        </RBACGuard>,
        { wrapper },
      );

      // Should render nothing (not even the children)
      expect(container.firstChild).toBeNull();
      expect(screen.queryByText("Delete Flow")).not.toBeInTheDocument();
    });

    it("should hide children when hideWhenDenied is true and user lacks permission", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false,
        isLoading: false,
        isSuccess: true,
      });

      const { container } = render(
        <RBACGuard
          check={{ permission: "Create", scope_type: "Flow", scope_id: null }}
          hideWhenDenied={true}
        >
          <button>New Flow</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(container.firstChild).toBeNull();
      expect(screen.queryByText("New Flow")).not.toBeInTheDocument();
    });
  });

  describe("Loading state", () => {
    it("should render loading spinner while checking permission", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: undefined,
        isLoading: true,
        isSuccess: false,
      });

      render(
        <RBACGuard
          check={{
            permission: "Delete",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
        >
          <button>Delete Flow</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.getByTestId("rbac-guard-loading")).toBeInTheDocument();
      expect(screen.queryByText("Delete Flow")).not.toBeInTheDocument();
    });

    it("should not render children or fallback during loading", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: undefined,
        isLoading: true,
        isSuccess: false,
      });

      render(
        <RBACGuard
          check={{
            permission: "Update",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
          fallback={<button disabled>Read-only</button>}
          hideWhenDenied={false}
        >
          <button>Save</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.getByTestId("rbac-guard-loading")).toBeInTheDocument();
      expect(screen.queryByText("Save")).not.toBeInTheDocument();
      expect(screen.queryByText("Read-only")).not.toBeInTheDocument();
    });
  });

  describe("Different permission types", () => {
    it("should work with Create permission", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <RBACGuard
          check={{ permission: "Create", scope_type: "Flow", scope_id: null }}
        >
          <button>New Flow</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.getByText("New Flow")).toBeInTheDocument();
    });

    it("should work with Read permission", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <RBACGuard
          check={{
            permission: "Read",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
        >
          <div>Flow Details</div>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.getByText("Flow Details")).toBeInTheDocument();
    });

    it("should work with Update permission", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <RBACGuard
          check={{
            permission: "Update",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
        >
          <button>Edit Flow</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.getByText("Edit Flow")).toBeInTheDocument();
    });

    it("should work with Delete permission", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <RBACGuard
          check={{
            permission: "Delete",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
        >
          <button>Delete Flow</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.getByText("Delete Flow")).toBeInTheDocument();
    });
  });

  describe("Different scope types", () => {
    it("should work with Flow scope", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <RBACGuard
          check={{
            permission: "Update",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
        >
          <button>Edit Flow</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.getByText("Edit Flow")).toBeInTheDocument();
      expect(usePermission).toHaveBeenCalledWith({
        permission: "Update",
        scope_type: "Flow",
        scope_id: "flow-123",
      });
    });

    it("should work with Project scope", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <RBACGuard
          check={{
            permission: "Delete",
            scope_type: "Project",
            scope_id: "project-456",
          }}
        >
          <button>Delete Project</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.getByText("Delete Project")).toBeInTheDocument();
      expect(usePermission).toHaveBeenCalledWith({
        permission: "Delete",
        scope_type: "Project",
        scope_id: "project-456",
      });
    });

    it("should work with null scope_id for global permissions", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <RBACGuard
          check={{ permission: "Create", scope_type: "Flow", scope_id: null }}
        >
          <button>New Flow</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.getByText("New Flow")).toBeInTheDocument();
      expect(usePermission).toHaveBeenCalledWith({
        permission: "Create",
        scope_type: "Flow",
        scope_id: null,
      });
    });
  });

  describe("Edge cases", () => {
    it("should handle undefined permission data gracefully", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: undefined,
        isLoading: false,
        isSuccess: false,
      });

      const { container } = render(
        <RBACGuard
          check={{
            permission: "Delete",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
        >
          <button>Delete Flow</button>
        </RBACGuard>,
        { wrapper },
      );

      // Should not render children when data is undefined
      expect(container.firstChild).toBeNull();
      expect(screen.queryByText("Delete Flow")).not.toBeInTheDocument();
    });

    it("should re-render when permission data changes", () => {
      const mockUsePermission = usePermission as jest.Mock;

      // Initially no permission
      mockUsePermission.mockReturnValue({
        data: false,
        isLoading: false,
        isSuccess: true,
      });

      const { rerender } = render(
        <RBACGuard
          check={{
            permission: "Delete",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
        >
          <button>Delete Flow</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.queryByText("Delete Flow")).not.toBeInTheDocument();

      // Permission granted
      mockUsePermission.mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      rerender(
        <RBACGuard
          check={{
            permission: "Delete",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
        >
          <button>Delete Flow</button>
        </RBACGuard>,
      );

      expect(screen.getByText("Delete Flow")).toBeInTheDocument();
    });

    it("should handle complex fallback content", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false,
        isLoading: false,
        isSuccess: true,
      });

      render(
        <RBACGuard
          check={{
            permission: "Update",
            scope_type: "Flow",
            scope_id: "flow-123",
          }}
          fallback={
            <div>
              <p>You do not have permission to edit this flow</p>
              <button disabled>Contact Admin</button>
            </div>
          }
          hideWhenDenied={false}
        >
          <button>Save</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(screen.queryByText("Save")).not.toBeInTheDocument();
      expect(
        screen.getByText("You do not have permission to edit this flow"),
      ).toBeInTheDocument();
      expect(screen.getByText("Contact Admin")).toBeInTheDocument();
      expect(screen.getByText("Contact Admin")).toBeDisabled();
    });

    it("should handle multiple RBACGuard instances independently", () => {
      const mockUsePermission = usePermission as jest.Mock;

      // First guard has permission, second doesn't
      mockUsePermission
        .mockReturnValueOnce({
          data: true,
          isLoading: false,
          isSuccess: true,
        })
        .mockReturnValueOnce({
          data: false,
          isLoading: false,
          isSuccess: true,
        });

      render(
        <div>
          <RBACGuard
            check={{
              permission: "Update",
              scope_type: "Flow",
              scope_id: "flow-123",
            }}
          >
            <button>Edit Flow</button>
          </RBACGuard>
          <RBACGuard
            check={{
              permission: "Delete",
              scope_type: "Flow",
              scope_id: "flow-123",
            }}
          >
            <button>Delete Flow</button>
          </RBACGuard>
        </div>,
        { wrapper },
      );

      expect(screen.getByText("Edit Flow")).toBeInTheDocument();
      expect(screen.queryByText("Delete Flow")).not.toBeInTheDocument();
    });
  });

  describe("Integration with usePermission hook", () => {
    it("should pass correct check parameters to usePermission", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      const check = {
        permission: "Update",
        scope_type: "Flow",
        scope_id: "flow-123",
      };

      render(
        <RBACGuard check={check}>
          <button>Save</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(usePermission).toHaveBeenCalledWith(check);
    });

    it("should handle permission check without scope_id", () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      const check = {
        permission: "Create",
        scope_type: "Flow",
        scope_id: null,
      };

      render(
        <RBACGuard check={check}>
          <button>New Flow</button>
        </RBACGuard>,
        { wrapper },
      );

      expect(usePermission).toHaveBeenCalledWith(check);
      expect(screen.getByText("New Flow")).toBeInTheDocument();
    });
  });
});
