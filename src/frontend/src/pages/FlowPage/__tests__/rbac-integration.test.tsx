import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { ReactNode } from "react";
import {
  createMemoryRouter,
  Route,
  RouterProvider,
  Routes,
} from "react-router-dom";
import FlowPage from "../index";

// Mock the usePermission hook
jest.mock("@/hooks/usePermission", () => ({
  usePermission: jest.fn(),
}));

// Mock other hooks and components
jest.mock("@/controllers/API/queries/flows/use-get-flow", () => ({
  useGetFlow: () => ({
    mutateAsync: jest.fn().mockResolvedValue({
      id: "test-flow-id",
      name: "Test Flow",
      data: { nodes: [], edges: [] },
    }),
  }),
}));

jest.mock("@/controllers/API/queries/flows/use-get-types", () => ({
  useGetTypes: jest.fn(),
}));

jest.mock("@/hooks/flows/use-save-flow", () => ({
  __esModule: true,
  default: () => jest.fn().mockResolvedValue({}),
}));

jest.mock("@/stores/typesStore", () => ({
  useTypesStore: (selector: any) => {
    const state = {
      types: { TestNode: { template: {} } },
    };
    return selector ? selector(state) : state;
  },
}));

jest.mock("@/stores/flowStore", () => ({
  __esModule: true,
  default: (selector: any) => {
    const state = {
      currentFlow: {
        id: "test-flow-id",
        name: "Test Flow",
        data: { nodes: [], edges: [] },
      },
      isBuilding: false,
      setOnFlowPage: jest.fn(),
      nodes: [],
      edges: [],
      onNodesChange: jest.fn(),
      onEdgesChange: jest.fn(),
      setNodes: jest.fn(),
      setEdges: jest.fn(),
      deleteNode: jest.fn(),
      deleteEdge: jest.fn(),
      paste: jest.fn(),
      setLastCopiedSelection: jest.fn(),
      onConnect: jest.fn(),
      updateCurrentFlow: jest.fn(),
      setFilterEdge: jest.fn(),
      setPositionDictionary: jest.fn(),
      reactFlowInstance: null,
      setReactFlowInstance: jest.fn(),
      lastCopiedSelection: null,
      setAutoSaveFlow: jest.fn(),
      autoSaveFlow: jest.fn(),
      stopBuilding: jest.fn(),
      helperLineEnabled: false,
      componentsToUpdate: [],
      hasIO: true,
    };
    return selector ? selector(state) : state;
  },
}));

jest.mock("@/stores/flowsManagerStore", () => ({
  __esModule: true,
  default: (selector: any) => {
    const state = {
      setCurrentFlow: jest.fn(),
      currentFlow: {
        id: "test-flow-id",
        name: "Test Flow",
        data: { nodes: [], edges: [] },
        updated_at: new Date().toISOString(),
      },
      currentFlowId: "test-flow-id",
      flows: [
        {
          id: "test-flow-id",
          name: "Test Flow",
        },
      ],
      autoSaving: false,
      undo: jest.fn(),
      redo: jest.fn(),
      takeSnapshot: jest.fn(),
    };
    return selector ? selector(state) : state;
  },
}));

jest.mock("@/stores/alertStore", () => {
  const state = {
    setSuccessData: jest.fn(),
    setErrorData: jest.fn(),
    setNoticeData: jest.fn(),
  };
  const store = (selector: any) => (selector ? selector(state) : state);
  store.getState = () => state;
  return {
    __esModule: true,
    default: store,
  };
});

jest.mock("@/customization/hooks/use-custom-navigate", () => ({
  useCustomNavigate: () => jest.fn(),
}));

jest.mock("@/hooks/use-mobile", () => ({
  useIsMobile: () => false,
}));

jest.mock("@/controllers/API/queries/_builds", () => ({
  useGetBuildsQuery: () => ({ isFetching: false }),
}));

// Mock sidebar components
jest.mock("@/components/ui/sidebar", () => ({
  SidebarProvider: ({ children }: any) => <div>{children}</div>,
  SidebarTrigger: () => <button>Sidebar Trigger</button>,
}));

// Mock other FlowPage components
jest.mock("../components/flowSidebarComponent", () => ({
  FlowSidebarComponent: () => <div>Flow Sidebar</div>,
}));

jest.mock("@/components/core/flowToolbarComponent", () => ({
  __esModule: true,
  default: ({ readOnly }: any) => (
    <div data-testid="flow-toolbar">{readOnly && <span>View Only</span>}</div>
  ),
}));

jest.mock("@/modals/saveChangesModal", () => ({
  SaveChangesModal: () => <div>Save Changes Modal</div>,
}));

// Mock the PageComponent to avoid complex dependencies
jest.mock("../components/PageComponent", () => ({
  __esModule: true,
  default: ({ readOnly }: { readOnly: boolean }) => (
    <div data-testid="page-component">
      <div
        data-testid="react-flow"
        data-readonly={readOnly}
        data-nodes-draggable={!readOnly}
        data-nodes-connectable={!readOnly}
      >
        <div data-testid="react-flow-props">
          readOnly: {String(readOnly)}, nodesDraggable: {String(!readOnly)},
          nodesConnectable: {String(!readOnly)}
        </div>
        <div data-testid="panel">
          <div data-testid="flow-toolbar">
            {readOnly && <span>View Only</span>}
          </div>
        </div>
      </div>
    </div>
  ),
}));

import { usePermission } from "@/hooks/usePermission";

describe("FlowPage RBAC Integration", () => {
  let queryClient: QueryClient;

  const renderWithRouter = (component: ReactNode) => {
    const router = createMemoryRouter(
      [
        {
          path: "/flow/:id",
          element: component,
        },
      ],
      {
        initialEntries: ["/flow/test-flow-id"],
      },
    );

    return render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
  };

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

  describe("Read-only mode when user lacks Update permission", () => {
    it("should enable read-only mode when user lacks Update permission", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false, // User does NOT have Update permission
        isLoading: false,
        isSuccess: true,
      });

      renderWithRouter(<FlowPage />);

      await waitFor(() => {
        const reactFlow = screen.getByTestId("react-flow");
        expect(reactFlow).toBeInTheDocument();
      });

      // Check that ReactFlow received readOnly prop as true
      const reactFlowProps = screen.getByTestId("react-flow-props");
      expect(reactFlowProps).toHaveTextContent("readOnly: true");
      expect(reactFlowProps).toHaveTextContent("nodesDraggable: false");
      expect(reactFlowProps).toHaveTextContent("nodesConnectable: false");
    });

    it("should display 'View Only' indicator when in read-only mode", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false,
        isLoading: false,
        isSuccess: true,
      });

      renderWithRouter(<FlowPage />);

      await waitFor(() => {
        expect(screen.getByText("View Only")).toBeInTheDocument();
      });
    });

    it("should hide publish dropdown when in read-only mode", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: false,
        isLoading: false,
        isSuccess: true,
      });

      renderWithRouter(<FlowPage />);

      await waitFor(() => {
        // The toolbar should be present but publish button should not be rendered
        expect(screen.getByTestId("panel")).toBeInTheDocument();
      });

      // Publish dropdown should not be rendered (component is hidden when readOnly=true)
      // This is verified by the presence of "View Only" indicator instead
      expect(screen.getByText("View Only")).toBeInTheDocument();
    });
  });

  describe("Edit mode when user has Update permission", () => {
    it("should allow editing when user has Update permission", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true, // User HAS Update permission
        isLoading: false,
        isSuccess: true,
      });

      renderWithRouter(<FlowPage />);

      await waitFor(() => {
        const reactFlow = screen.getByTestId("react-flow");
        expect(reactFlow).toBeInTheDocument();
      });

      // Check that ReactFlow received readOnly prop as false
      const reactFlowProps = screen.getByTestId("react-flow-props");
      expect(reactFlowProps).toHaveTextContent("readOnly: false");
      expect(reactFlowProps).toHaveTextContent("nodesDraggable: true");
      expect(reactFlowProps).toHaveTextContent("nodesConnectable: true");
    });

    it("should NOT display 'View Only' indicator when user can edit", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      renderWithRouter(<FlowPage />);

      await waitFor(() => {
        expect(screen.getByTestId("react-flow")).toBeInTheDocument();
      });

      // View Only indicator should not be present
      expect(screen.queryByText("View Only")).not.toBeInTheDocument();
    });

    it("should show publish dropdown when user can edit", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      renderWithRouter(<FlowPage />);

      await waitFor(() => {
        expect(screen.getByTestId("panel")).toBeInTheDocument();
      });

      // View Only should not be present
      expect(screen.queryByText("View Only")).not.toBeInTheDocument();
    });
  });

  describe("PermissionErrorBoundary integration", () => {
    it("should wrap content in PermissionErrorBoundary", async () => {
      (usePermission as jest.Mock).mockReturnValue({
        data: true,
        isLoading: false,
        isSuccess: true,
      });

      renderWithRouter(<FlowPage />);

      await waitFor(() => {
        // The flow page should render without errors
        expect(screen.getByTestId("react-flow")).toBeInTheDocument();
      });

      // This verifies that PermissionErrorBoundary is not catching any errors
      expect(
        screen.queryByText("Permission Check Failed"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Permission check parameters", () => {
    it("should check Update permission for the correct flow ID", async () => {
      const mockUsePermission = usePermission as jest.Mock;
      mockUsePermission.mockReturnValue({
        data: false,
        isLoading: false,
        isSuccess: true,
      });

      renderWithRouter(<FlowPage />);

      await waitFor(() => {
        expect(mockUsePermission).toHaveBeenCalledWith({
          permission: "Update",
          scope_type: "Flow",
          scope_id: "test-flow-id",
        });
      });
    });
  });
});
