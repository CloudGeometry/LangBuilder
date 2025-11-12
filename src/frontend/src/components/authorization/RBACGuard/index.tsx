import { ReactNode } from "react";
import { PermissionCheck, usePermission } from "@/hooks/usePermission";

/**
 * Props for the RBACGuard component.
 */
interface RBACGuardProps {
  /** Permission check parameters */
  check: PermissionCheck;
  /** Content to render when user has permission */
  children: ReactNode;
  /** Optional content to show when user lacks permission */
  fallback?: ReactNode;
  /** If true, render nothing when permission is denied. If false, render fallback. Default: true */
  hideWhenDenied?: boolean;
}

/**
 * RBACGuard component for permission-based UI rendering.
 * Conditionally renders children based on user permissions.
 *
 * @component
 * @example
 * ```tsx
 * // Hide button when user lacks permission
 * <RBACGuard check={{ permission: "Delete", scope_type: "Flow", scope_id: flowId }}>
 *   <Button onClick={handleDelete}>Delete Flow</Button>
 * </RBACGuard>
 *
 * // Show disabled button when user lacks permission
 * <RBACGuard
 *   check={{ permission: "Update", scope_type: "Flow", scope_id: flowId }}
 *   fallback={<Button disabled>Save (Read-only)</Button>}
 *   hideWhenDenied={false}
 * >
 *   <Button onClick={handleSave}>Save</Button>
 * </RBACGuard>
 * ```
 */
export default function RBACGuard({
  check,
  children,
  fallback = null,
  hideWhenDenied = true,
}: RBACGuardProps) {
  const { data: hasPermission, isLoading } = usePermission(check);

  // Show loading spinner while checking permission
  if (isLoading) {
    return (
      <div className="loading-spinner" data-testid="rbac-guard-loading">
        {/* Empty loading state - can be customized with a spinner component */}
      </div>
    );
  }

  // User lacks permission
  if (!hasPermission) {
    // Either hide completely or show fallback content
    return hideWhenDenied ? null : <>{fallback}</>;
  }

  // User has permission - render children
  return <>{children}</>;
}
