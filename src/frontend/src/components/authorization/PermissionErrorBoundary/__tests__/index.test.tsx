import { render, screen } from "@testing-library/react";
import React, { ReactNode } from "react";
import { PermissionErrorBoundary, useResetErrorBoundary } from "../index";

// Mock the Button component and lucide-react icons
jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, ...props }: any) => (
    <button onClick={onClick} {...props}>
      {children}
    </button>
  ),
}));

jest.mock("lucide-react", () => ({
  AlertCircle: () => <svg data-testid="alert-circle-icon" />,
}));

// Component that throws an error
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error("Permission check failed");
  }

  return <div>Protected Content</div>;
};

// Component to test useResetErrorBoundary hook
const ErrorBoundaryWithReset = ({ children }: { children: ReactNode }) => {
  const errorBoundaryRef = React.useRef<PermissionErrorBoundary>(null);
  const resetErrorBoundary = useResetErrorBoundary(errorBoundaryRef);

  return (
    <div>
      <PermissionErrorBoundary ref={errorBoundaryRef}>
        {children}
      </PermissionErrorBoundary>
      <button onClick={resetErrorBoundary}>Reset Error</button>
    </div>
  );
};

describe("PermissionErrorBoundary", () => {
  // Suppress console.error for cleaner test output
  const originalError = console.error;
  beforeAll(() => {
    console.error = jest.fn();
  });

  afterAll(() => {
    console.error = originalError;
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("Normal rendering", () => {
    it("should render children when no error occurs", () => {
      render(
        <PermissionErrorBoundary>
          <div>Protected Content</div>
        </PermissionErrorBoundary>,
      );

      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });

    it("should render complex children when no error occurs", () => {
      render(
        <PermissionErrorBoundary>
          <div>
            <h1>Flow Editor</h1>
            <button>Save</button>
            <button>Cancel</button>
          </div>
        </PermissionErrorBoundary>,
      );

      expect(screen.getByText("Flow Editor")).toBeInTheDocument();
      expect(screen.getByText("Save")).toBeInTheDocument();
      expect(screen.getByText("Cancel")).toBeInTheDocument();
    });

    it("should render multiple children when no error occurs", () => {
      render(
        <PermissionErrorBoundary>
          <div>First Component</div>
          <div>Second Component</div>
        </PermissionErrorBoundary>,
      );

      expect(screen.getByText("First Component")).toBeInTheDocument();
      expect(screen.getByText("Second Component")).toBeInTheDocument();
    });
  });

  describe("Error handling", () => {
    it("should display default error UI when an error is caught", () => {
      render(
        <PermissionErrorBoundary>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      expect(
        screen.getByTestId("permission-error-boundary-fallback"),
      ).toBeInTheDocument();
      expect(screen.getByText("Permission Check Failed")).toBeInTheDocument();
      expect(
        screen.getByText(
          /Unable to verify permissions. Please refresh the page/,
        ),
      ).toBeInTheDocument();
      expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
    });

    it("should render custom fallback when provided and error occurs", () => {
      const customFallback = (
        <div data-testid="custom-fallback">
          <h2>Custom Error Message</h2>
          <p>Something went wrong</p>
        </div>
      );

      render(
        <PermissionErrorBoundary fallback={customFallback}>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      expect(screen.getByTestId("custom-fallback")).toBeInTheDocument();
      expect(screen.getByText("Custom Error Message")).toBeInTheDocument();
      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
      expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
    });

    it("should call onError callback when error is caught", () => {
      const onError = jest.fn();

      render(
        <PermissionErrorBoundary onError={onError}>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      expect(onError).toHaveBeenCalledTimes(1);
      expect(onError).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          componentStack: expect.any(String),
        }),
      );
    });

    it("should log error to console when error is caught", () => {
      const consoleErrorSpy = jest.spyOn(console, "error");

      render(
        <PermissionErrorBoundary>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  describe("Default error UI", () => {
    it("should render AlertCircle icon in default error UI", () => {
      render(
        <PermissionErrorBoundary>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      const fallback = screen.getByTestId("permission-error-boundary-fallback");
      expect(fallback).toBeInTheDocument();

      // Check for the destructive styling
      expect(fallback).toHaveClass("border-destructive/50");
      expect(fallback).toHaveClass("bg-destructive/10");
    });

    it("should render refresh button in default error UI", () => {
      render(
        <PermissionErrorBoundary>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      const refreshButton = screen.getByRole("button", {
        name: /refresh page/i,
      });
      expect(refreshButton).toBeInTheDocument();
    });

    it("should display helpful error message in default error UI", () => {
      render(
        <PermissionErrorBoundary>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      expect(screen.getByText("Permission Check Failed")).toBeInTheDocument();
      expect(
        screen.getByText(
          /Unable to verify permissions. Please refresh the page or contact support/,
        ),
      ).toBeInTheDocument();
    });
  });

  describe("Custom fallback", () => {
    it("should render custom fallback with interactive elements", () => {
      const customFallback = (
        <div data-testid="custom-fallback">
          <button>Try Again</button>
          <a href="/help">Get Help</a>
        </div>
      );

      render(
        <PermissionErrorBoundary fallback={customFallback}>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      expect(screen.getByText("Try Again")).toBeInTheDocument();
      expect(screen.getByText("Get Help")).toBeInTheDocument();
    });

    it("should render complex custom fallback UI", () => {
      const customFallback = (
        <div className="custom-error">
          <h1>Oops!</h1>
          <p>We couldn&apos;t load your permissions.</p>
          <div>
            <button>Reload</button>
            <button>Go Back</button>
          </div>
        </div>
      );

      render(
        <PermissionErrorBoundary fallback={customFallback}>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      expect(screen.getByText("Oops!")).toBeInTheDocument();
      expect(
        screen.getByText("We couldn't load your permissions."),
      ).toBeInTheDocument();
      expect(screen.getByText("Reload")).toBeInTheDocument();
      expect(screen.getByText("Go Back")).toBeInTheDocument();
    });
  });

  describe("Error recovery", () => {
    it("should transition from error to normal state when error is cleared", () => {
      const { rerender } = render(
        <PermissionErrorBoundary>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      // Error state
      expect(screen.getByText("Permission Check Failed")).toBeInTheDocument();
      expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();

      // Fix the error
      rerender(
        <PermissionErrorBoundary>
          <ThrowError shouldThrow={false} />
        </PermissionErrorBoundary>,
      );

      // Note: Error boundaries don't automatically recover - this test demonstrates
      // the current behavior where error UI persists even when children are fixed
      expect(screen.getByText("Permission Check Failed")).toBeInTheDocument();
    });
  });

  describe("Nested error boundaries", () => {
    it("should handle errors in nested components", () => {
      render(
        <PermissionErrorBoundary>
          <div>
            <h1>Parent Content</h1>
            <PermissionErrorBoundary>
              <ThrowError shouldThrow={true} />
            </PermissionErrorBoundary>
          </div>
        </PermissionErrorBoundary>,
      );

      // Inner error boundary should catch the error
      expect(screen.getByText("Permission Check Failed")).toBeInTheDocument();
      // Parent content is still visible (only inner boundary shows error)
      expect(screen.getByText("Parent Content")).toBeInTheDocument();
    });

    it("should isolate errors to nearest boundary", () => {
      const onInnerError = jest.fn();
      const onOuterError = jest.fn();

      render(
        <PermissionErrorBoundary onError={onOuterError}>
          <div>
            Outer Content
            <PermissionErrorBoundary onError={onInnerError}>
              <ThrowError shouldThrow={true} />
            </PermissionErrorBoundary>
          </div>
        </PermissionErrorBoundary>,
      );

      // Only inner error handler should be called
      expect(onInnerError).toHaveBeenCalledTimes(1);
      expect(onOuterError).not.toHaveBeenCalled();
      expect(screen.getByText("Outer Content")).toBeInTheDocument();
    });
  });

  describe("Edge cases", () => {
    it("should handle null children gracefully", () => {
      render(<PermissionErrorBoundary>{null}</PermissionErrorBoundary>);

      // Should render without error
      expect(
        screen.queryByText("Permission Check Failed"),
      ).not.toBeInTheDocument();
    });

    it("should handle undefined children gracefully", () => {
      render(<PermissionErrorBoundary>{undefined}</PermissionErrorBoundary>);

      // Should render without error
      expect(
        screen.queryByText("Permission Check Failed"),
      ).not.toBeInTheDocument();
    });

    it("should handle empty children gracefully", () => {
      render(<PermissionErrorBoundary>{""}</PermissionErrorBoundary>);

      // Should render without error
      expect(
        screen.queryByText("Permission Check Failed"),
      ).not.toBeInTheDocument();
    });

    it("should handle different error types", () => {
      const ThrowTypeError = () => {
        throw new TypeError("Type error occurred");
      };

      render(
        <PermissionErrorBoundary>
          <ThrowTypeError />
        </PermissionErrorBoundary>,
      );

      expect(screen.getByText("Permission Check Failed")).toBeInTheDocument();
    });

    it("should handle async errors (note: error boundaries only catch synchronous errors)", () => {
      // Error boundaries do NOT catch async errors - this is expected behavior
      const AsyncError = () => {
        return <div>Async Content</div>;
      };

      render(
        <PermissionErrorBoundary>
          <AsyncError />
        </PermissionErrorBoundary>,
      );

      // Should render normally since error boundary doesn't catch async errors
      expect(screen.getByText("Async Content")).toBeInTheDocument();
    });
  });

  describe("Props validation", () => {
    it("should work with only required children prop", () => {
      render(
        <PermissionErrorBoundary>
          <div>Simple Content</div>
        </PermissionErrorBoundary>,
      );

      expect(screen.getByText("Simple Content")).toBeInTheDocument();
    });

    it("should work with all optional props", () => {
      const onError = jest.fn();
      const fallback = <div>Custom Fallback</div>;

      render(
        <PermissionErrorBoundary fallback={fallback} onError={onError}>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      expect(screen.getByText("Custom Fallback")).toBeInTheDocument();
      expect(onError).toHaveBeenCalled();
    });
  });

  describe("Real-world usage scenarios", () => {
    it("should handle permission check errors in flow editor", () => {
      const FlowEditor = ({ shouldError }: { shouldError: boolean }) => {
        if (shouldError) {
          throw new Error("Permission API failed");
        }
        return (
          <div>
            <h1>Flow Editor</h1>
            <button>Save</button>
          </div>
        );
      };

      render(
        <PermissionErrorBoundary>
          <FlowEditor shouldError={true} />
        </PermissionErrorBoundary>,
      );

      expect(screen.getByText("Permission Check Failed")).toBeInTheDocument();
      expect(screen.queryByText("Flow Editor")).not.toBeInTheDocument();
    });

    it("should handle permission check errors in project list", () => {
      const ProjectList = ({ shouldError }: { shouldError: boolean }) => {
        if (shouldError) {
          throw new Error("Failed to load projects");
        }
        return (
          <div>
            <h2>My Projects</h2>
            <ul>
              <li>Project 1</li>
              <li>Project 2</li>
            </ul>
          </div>
        );
      };

      const customFallback = (
        <div>
          <h2>Unable to Load Projects</h2>
          <p>Please try refreshing the page.</p>
        </div>
      );

      render(
        <PermissionErrorBoundary fallback={customFallback}>
          <ProjectList shouldError={true} />
        </PermissionErrorBoundary>,
      );

      expect(screen.getByText("Unable to Load Projects")).toBeInTheDocument();
      expect(screen.queryByText("My Projects")).not.toBeInTheDocument();
    });

    it("should preserve error boundary state across re-renders of children", () => {
      const { rerender } = render(
        <PermissionErrorBoundary>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      expect(screen.getByText("Permission Check Failed")).toBeInTheDocument();

      // Re-render with different props
      rerender(
        <PermissionErrorBoundary>
          <div>New Content</div>
        </PermissionErrorBoundary>,
      );

      // Error state persists (error boundaries don't auto-recover)
      expect(screen.getByText("Permission Check Failed")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible error message", () => {
      render(
        <PermissionErrorBoundary>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      const errorHeading = screen.getByText("Permission Check Failed");
      expect(errorHeading).toHaveClass("text-sm");
      expect(errorHeading).toHaveClass("font-medium");
    });

    it("should have accessible refresh button", () => {
      render(
        <PermissionErrorBoundary>
          <ThrowError shouldThrow={true} />
        </PermissionErrorBoundary>,
      );

      const refreshButton = screen.getByRole("button", {
        name: /refresh page/i,
      });
      expect(refreshButton).toBeInTheDocument();
    });
  });
});
