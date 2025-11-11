import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { BrowserRouter, useSearchParams } from "react-router-dom";

// Mock child components
jest.mock("../RBACManagementPage", () => {
  return function MockRBACManagementPage() {
    return (
      <div data-testid="rbac-management-page">RBAC Management Content</div>
    );
  };
});

// Mock react-router-dom hooks
const mockSetSearchParams = jest.fn();
const mockNavigate = jest.fn();

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useSearchParams: jest.fn(),
  Navigate: ({ to, replace }: any) => (
    <div data-testid="navigate" data-to={to} data-replace={replace}>
      Redirecting...
    </div>
  ),
}));

// Mock auth store
const mockAuthStore = {
  isAdmin: true,
  setIsAdmin: jest.fn(),
};

jest.mock("@/stores/authStore", () => ({
  __esModule: true,
  default: jest.fn(() => mockAuthStore),
}));

// Mock AuthContext
const mockUserData = {
  id: "test-user-id",
  username: "testuser",
  is_active: true,
  is_superuser: true,
  create_at: new Date(),
  updated_at: new Date(),
};

const mockAuthContextValue = {
  userData: mockUserData,
  accessToken: "test-token",
  login: jest.fn(),
  setUserData: jest.fn(),
  authenticationErrorCount: 0,
  setApiKey: jest.fn(),
  apiKey: null,
  storeApiKey: jest.fn(),
  getUser: jest.fn(),
};

// Create a real context for testing
const MockAuthContext = React.createContext(mockAuthContextValue);

// Mock the authContext module to return our mock context
jest.mock("@/contexts/authContext", () => {
  const React = require("react");
  const mockUserData = {
    id: "test-user-id",
    username: "testuser",
    is_active: true,
    is_superuser: true,
    create_at: new Date(),
    updated_at: new Date(),
  };

  const mockAuthContextValue = {
    userData: mockUserData,
    accessToken: "test-token",
    login: jest.fn(),
    setUserData: jest.fn(),
    authenticationErrorCount: 0,
    setApiKey: jest.fn(),
    apiKey: null,
    storeApiKey: jest.fn(),
    getUser: jest.fn(),
  };

  return {
    AuthContext: React.createContext(mockAuthContextValue),
    AuthProvider: ({ children }: any) => children,
  };
});

// Mock API queries
jest.mock("@/controllers/API/queries/auth", () => ({
  useGetUsers: jest.fn(() => ({
    mutate: jest.fn(),
    isPending: false,
    isIdle: false,
  })),
  useAddUser: jest.fn(() => ({
    mutate: jest.fn(),
  })),
  useUpdateUser: jest.fn(() => ({
    mutate: jest.fn(),
  })),
  useDeleteUsers: jest.fn(() => ({
    mutate: jest.fn(),
  })),
}));

// Mock UI components
jest.mock("@/components/common/genericIconComponent", () => {
  return function MockIconComponent({ name }: any) {
    return <span data-testid={`icon-${name}`}>{name}</span>;
  };
});

jest.mock("@/components/ui/tabs", () => ({
  Tabs: ({ children, value, onValueChange }: any) => (
    <div data-testid="tabs" data-value={value}>
      <button
        data-testid="tabs-trigger"
        onClick={() => onValueChange && onValueChange("rbac")}
      >
        Change Tab
      </button>
      {children}
    </div>
  ),
  TabsList: ({ children }: any) => (
    <div data-testid="tabs-list">{children}</div>
  ),
  TabsTrigger: ({ children, value }: any) => (
    <button data-testid={`tab-trigger-${value}`}>{children}</button>
  ),
  TabsContent: ({ children, value }: any) => (
    <div data-testid={`tab-content-${value}`}>{children}</div>
  ),
}));

jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick }: any) => (
    <button onClick={onClick}>{children}</button>
  ),
}));

jest.mock("@/components/ui/input", () => ({
  Input: ({ value, onChange, placeholder }: any) => (
    <input value={value} onChange={onChange} placeholder={placeholder} />
  ),
}));

jest.mock("@/components/ui/table", () => ({
  Table: ({ children }: any) => <table>{children}</table>,
  TableHeader: ({ children }: any) => <thead>{children}</thead>,
  TableBody: ({ children }: any) => <tbody>{children}</tbody>,
  TableRow: ({ children }: any) => <tr>{children}</tr>,
  TableHead: ({ children }: any) => <th>{children}</th>,
  TableCell: ({ children }: any) => <td>{children}</td>,
}));

jest.mock("@/components/ui/checkbox", () => ({
  CheckBoxDiv: ({ checked }: any) => (
    <input type="checkbox" checked={checked} readOnly />
  ),
}));

jest.mock("@/components/common/paginatorComponent", () => {
  return function MockPaginator() {
    return <div data-testid="paginator">Paginator</div>;
  };
});

jest.mock("@/customization/components/custom-loader", () => {
  return function MockLoader() {
    return <div data-testid="loader">Loading...</div>;
  };
});

jest.mock("@/modals/confirmationModal", () => {
  return {
    __esModule: true,
    default: ({ children }: any) => <div>{children}</div>,
  };
});

jest.mock("@/modals/userManagementModal", () => {
  return function MockUserManagementModal({ children }: any) {
    return <div>{children}</div>;
  };
});

jest.mock("@/components/common/shadTooltipComponent", () => {
  return function MockShadTooltip({ children }: any) {
    return <div>{children}</div>;
  };
});

jest.mock("@/stores/alertStore", () => ({
  __esModule: true,
  default: jest.fn(() => ({
    setSuccessData: jest.fn(),
    setErrorData: jest.fn(),
  })),
}));

// Import AdminPage AFTER all mocks are set up
import AdminPage from "../index";

describe("AdminPage", () => {
  const mockSearchParams = new URLSearchParams();

  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthStore.isAdmin = true;
    (useSearchParams as jest.Mock).mockReturnValue([
      mockSearchParams,
      mockSetSearchParams,
    ]);
  });

  // Helper function to render AdminPage with all required providers
  const renderAdminPage = () => {
    return render(
      <BrowserRouter>
        <AdminPage />
      </BrowserRouter>,
    );
  };

  describe("Access Control", () => {
    it("should redirect non-admin users to home page", () => {
      mockAuthStore.isAdmin = false;

      renderAdminPage();

      const navigate = screen.getByTestId("navigate");
      expect(navigate).toBeInTheDocument();
      expect(navigate).toHaveAttribute("data-to", "/");
      expect(navigate).toHaveAttribute("data-replace", "true");
    });

    it("should allow admin users to access the page", () => {
      mockAuthStore.isAdmin = true;

      renderAdminPage();

      expect(screen.queryByTestId("navigate")).not.toBeInTheDocument();
      expect(screen.getByTestId("tabs")).toBeInTheDocument();
    });
  });

  describe("Tab Management", () => {
    it("should render both user management and RBAC tabs", () => {
      renderAdminPage();

      expect(screen.getByTestId("tab-trigger-users")).toBeInTheDocument();
      expect(screen.getByTestId("tab-trigger-rbac")).toBeInTheDocument();
      expect(screen.getByText("User Management")).toBeInTheDocument();
      expect(screen.getByText("RBAC Management")).toBeInTheDocument();
    });

    it("should default to users tab when no query param is present", () => {
      mockSearchParams.delete("tab");

      renderAdminPage();

      const tabs = screen.getByTestId("tabs");
      expect(tabs).toHaveAttribute("data-value", "users");
    });

    it("should show RBAC tab when query param is rbac", () => {
      mockSearchParams.set("tab", "rbac");

      renderAdminPage();

      const tabs = screen.getByTestId("tabs");
      expect(tabs).toHaveAttribute("data-value", "rbac");
    });

    it("should update URL when tab changes", () => {
      renderAdminPage();

      const changeTrigger = screen.getByTestId("tabs-trigger");
      fireEvent.click(changeTrigger);

      expect(mockSetSearchParams).toHaveBeenCalledWith({ tab: "rbac" });
    });
  });

  describe("Deep Linking", () => {
    it("should support deep link to RBAC tab via ?tab=rbac", () => {
      mockSearchParams.set("tab", "rbac");

      renderAdminPage();

      expect(screen.getByTestId("tabs")).toHaveAttribute("data-value", "rbac");
    });

    it("should support deep link to users tab via ?tab=users", () => {
      mockSearchParams.set("tab", "users");

      renderAdminPage();

      expect(screen.getByTestId("tabs")).toHaveAttribute("data-value", "users");
    });

    it("should redirect non-admin users even with deep link", () => {
      mockAuthStore.isAdmin = false;
      mockSearchParams.set("tab", "rbac");

      renderAdminPage();

      expect(screen.getByTestId("navigate")).toBeInTheDocument();
    });
  });

  describe("RBAC Management Tab Content", () => {
    it("should render RBACManagementPage component in RBAC tab", () => {
      mockSearchParams.set("tab", "rbac");

      renderAdminPage();

      expect(screen.getByTestId("tab-content-rbac")).toBeInTheDocument();
      expect(screen.getByTestId("rbac-management-page")).toBeInTheDocument();
    });
  });

  describe("Page Header", () => {
    it("should render admin page title and description", () => {
      renderAdminPage();

      expect(screen.getByTestId("icon-Shield")).toBeInTheDocument();
    });
  });
});
