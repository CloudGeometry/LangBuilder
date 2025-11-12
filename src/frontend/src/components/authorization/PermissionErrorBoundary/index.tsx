import { AlertCircle } from "lucide-react";
import React, { Component, ErrorInfo, ReactNode } from "react";
import { Button } from "@/components/ui/button";

/**
 * Props for the PermissionErrorBoundary component.
 */
interface Props {
  /** Content to render when no error occurs */
  children: ReactNode;
  /** Optional custom fallback UI to show when an error is caught */
  fallback?: ReactNode;
  /** Optional callback when an error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

/**
 * State for the PermissionErrorBoundary component.
 */
interface State {
  /** Whether an error has been caught */
  hasError: boolean;
  /** The error that was caught, if any */
  error: Error | null;
}

/**
 * Error boundary component for catching and handling permission check errors.
 * Wraps components that perform permission checks and provides graceful error handling.
 *
 * @component
 * @example
 * ```tsx
 * // Basic usage with default error UI
 * <PermissionErrorBoundary>
 *   <ProtectedComponent />
 * </PermissionErrorBoundary>
 *
 * // Custom fallback UI
 * <PermissionErrorBoundary
 *   fallback={
 *     <div>
 *       <h2>Unable to Load</h2>
 *       <Button onClick={() => window.location.reload()}>Refresh</Button>
 *     </div>
 *   }
 * >
 *   <ProtectedComponent />
 * </PermissionErrorBoundary>
 *
 * // With error callback
 * <PermissionErrorBoundary
 *   onError={(error, errorInfo) => {
 *     console.error('Permission error:', error, errorInfo);
 *   }}
 * >
 *   <ProtectedComponent />
 * </PermissionErrorBoundary>
 * ```
 */
export class PermissionErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  /**
   * Static method to update state when an error is caught.
   */
  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  /**
   * Lifecycle method called when an error is caught.
   * Logs the error and calls the optional onError callback.
   */
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Permission check error:", error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  /**
   * Renders the component.
   * Shows error UI if an error was caught, otherwise renders children.
   */
  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div
          className="flex items-center gap-2 rounded-md border border-destructive/50 bg-destructive/10 p-4"
          data-testid="permission-error-boundary-fallback"
        >
          <AlertCircle className="h-5 w-5 text-destructive" />
          <div>
            <h3 className="text-sm font-medium text-destructive">
              Permission Check Failed
            </h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Unable to verify permissions. Please refresh the page or contact
              support if the issue persists.
            </p>
            <Button
              onClick={() => window.location.reload()}
              variant="outline"
              size="sm"
              className="mt-2"
            >
              Refresh Page
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Hook for resetting the error boundary state.
 * Useful for retry mechanisms or manual error clearing.
 *
 * @param errorBoundaryRef - React ref to the PermissionErrorBoundary component
 * @returns Function to reset the error boundary state
 *
 * @example
 * ```tsx
 * const errorBoundaryRef = useRef<PermissionErrorBoundary>(null);
 * const resetErrorBoundary = useResetErrorBoundary(errorBoundaryRef);
 *
 * return (
 *   <PermissionErrorBoundary ref={errorBoundaryRef}>
 *     <ProtectedComponent />
 *   </PermissionErrorBoundary>
 * );
 * ```
 */
export function useResetErrorBoundary(
  errorBoundaryRef: React.RefObject<PermissionErrorBoundary>,
) {
  return () => {
    errorBoundaryRef.current?.setState({ hasError: false, error: null });
  };
}
