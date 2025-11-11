import { fireEvent, render, screen } from "@testing-library/react";
import RBACManagementPage from "../index";

// Mock child components
jest.mock("../AssignmentListView", () => {
  return function MockAssignmentListView({ onEditAssignment }: any) {
    return (
      <div data-testid="assignment-list-view">
        <button
          data-testid="trigger-edit"
          onClick={() => onEditAssignment("test-assignment-id")}
        >
          Edit Assignment
        </button>
      </div>
    );
  };
});

jest.mock("../CreateAssignmentModal", () => {
  return function MockCreateAssignmentModal({ open, onClose, onSuccess }: any) {
    return open ? (
      <div data-testid="create-assignment-modal">
        <button data-testid="modal-close" onClick={onClose}>
          Close
        </button>
        <button data-testid="modal-success" onClick={onSuccess}>
          Success
        </button>
      </div>
    ) : null;
  };
});

jest.mock("../EditAssignmentModal", () => {
  return function MockEditAssignmentModal({
    open,
    assignmentId,
    onClose,
    onSuccess,
  }: any) {
    return open ? (
      <div data-testid="edit-assignment-modal">
        <span data-testid="assignment-id">{assignmentId}</span>
        <button data-testid="modal-close" onClick={onClose}>
          Close
        </button>
        <button data-testid="modal-success" onClick={onSuccess}>
          Success
        </button>
      </div>
    ) : null;
  };
});

// Mock IconComponent
jest.mock("@/components/common/genericIconComponent", () => {
  return function MockIconComponent({ name, className }: any) {
    return <span data-testid={`icon-${name}`} className={className} />;
  };
});

// Mock Button component
jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, ...props }: any) => (
    <button onClick={onClick} {...props}>
      {children}
    </button>
  ),
}));

describe("RBACManagementPage", () => {
  describe("Rendering", () => {
    it("should render the page title and description", () => {
      render(<RBACManagementPage />);

      expect(screen.getByText("Role-Based Access Control")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Manage role assignments for users across projects and flows",
        ),
      ).toBeInTheDocument();
    });

    it("should render the info banner with inheritance message", () => {
      render(<RBACManagementPage />);

      expect(screen.getByTestId("icon-Info")).toBeInTheDocument();
      expect(
        screen.getByText(
          /Project-level assignments are inherited by contained Flows/,
        ),
      ).toBeInTheDocument();
    });

    it("should render the New Assignment button", () => {
      render(<RBACManagementPage />);

      const newButton = screen.getByText("New Assignment");
      expect(newButton).toBeInTheDocument();
      expect(screen.getByTestId("icon-Plus")).toBeInTheDocument();
    });

    it("should render the AssignmentListView component", () => {
      render(<RBACManagementPage />);

      expect(screen.getByTestId("assignment-list-view")).toBeInTheDocument();
    });
  });

  describe("Create Assignment Modal", () => {
    it("should open create modal when New Assignment button is clicked", () => {
      render(<RBACManagementPage />);

      const newButton = screen.getByText("New Assignment");
      fireEvent.click(newButton);

      expect(screen.getByTestId("create-assignment-modal")).toBeInTheDocument();
    });

    it("should close create modal when onClose is called", () => {
      render(<RBACManagementPage />);

      // Open modal
      const newButton = screen.getByText("New Assignment");
      fireEvent.click(newButton);
      expect(screen.getByTestId("create-assignment-modal")).toBeInTheDocument();

      // Close modal
      const closeButton = screen.getByTestId("modal-close");
      fireEvent.click(closeButton);
      expect(
        screen.queryByTestId("create-assignment-modal"),
      ).not.toBeInTheDocument();
    });

    it("should close create modal when onSuccess is called", () => {
      render(<RBACManagementPage />);

      // Open modal
      const newButton = screen.getByText("New Assignment");
      fireEvent.click(newButton);
      expect(screen.getByTestId("create-assignment-modal")).toBeInTheDocument();

      // Trigger success
      const successButton = screen.getByTestId("modal-success");
      fireEvent.click(successButton);
      expect(
        screen.queryByTestId("create-assignment-modal"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Edit Assignment Modal", () => {
    it("should open edit modal when onEditAssignment is called with an ID", () => {
      render(<RBACManagementPage />);

      // Trigger edit from AssignmentListView
      const editButton = screen.getByTestId("trigger-edit");
      fireEvent.click(editButton);

      expect(screen.getByTestId("edit-assignment-modal")).toBeInTheDocument();
      expect(screen.getByTestId("assignment-id")).toHaveTextContent(
        "test-assignment-id",
      );
    });

    it("should close edit modal when onClose is called", () => {
      render(<RBACManagementPage />);

      // Open edit modal
      const editButton = screen.getByTestId("trigger-edit");
      fireEvent.click(editButton);
      expect(screen.getByTestId("edit-assignment-modal")).toBeInTheDocument();

      // Close modal
      const closeButton = screen.getByTestId("modal-close");
      fireEvent.click(closeButton);
      expect(
        screen.queryByTestId("edit-assignment-modal"),
      ).not.toBeInTheDocument();
    });

    it("should close edit modal and clear selection when onSuccess is called", () => {
      render(<RBACManagementPage />);

      // Open edit modal
      const editButton = screen.getByTestId("trigger-edit");
      fireEvent.click(editButton);
      expect(screen.getByTestId("edit-assignment-modal")).toBeInTheDocument();

      // Trigger success
      const successButton = screen.getByTestId("modal-success");
      fireEvent.click(successButton);
      expect(
        screen.queryByTestId("edit-assignment-modal"),
      ).not.toBeInTheDocument();
    });

    it("should not render edit modal when no assignment is selected", () => {
      render(<RBACManagementPage />);

      expect(
        screen.queryByTestId("edit-assignment-modal"),
      ).not.toBeInTheDocument();
    });
  });

  describe("State Management", () => {
    it("should manage modal open/close state independently", () => {
      render(<RBACManagementPage />);

      // Open create modal
      const newButton = screen.getByText("New Assignment");
      fireEvent.click(newButton);
      expect(screen.getByTestId("create-assignment-modal")).toBeInTheDocument();
      expect(
        screen.queryByTestId("edit-assignment-modal"),
      ).not.toBeInTheDocument();

      // Close create modal
      fireEvent.click(screen.getByTestId("modal-close"));
      expect(
        screen.queryByTestId("create-assignment-modal"),
      ).not.toBeInTheDocument();

      // Open edit modal
      const editButton = screen.getByTestId("trigger-edit");
      fireEvent.click(editButton);
      expect(screen.getByTestId("edit-assignment-modal")).toBeInTheDocument();
      expect(
        screen.queryByTestId("create-assignment-modal"),
      ).not.toBeInTheDocument();
    });
  });
});
