import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/controllers/API";

/**
 * Permission check parameters for RBAC authorization.
 */
export interface PermissionCheck {
  /** Permission to check: "Create", "Read", "Update", "Delete" */
  permission: string;
  /** Resource type: "Flow", "Project" */
  scope_type: string;
  /** Optional resource ID for resource-level checks */
  scope_id: string | null;
}

/**
 * Hook to check if the current user has a specific permission.
 * Uses TanStack Query for caching and automatic refetching.
 *
 * @param check - Permission check parameters
 * @returns Query result with hasPermission boolean and loading/error states
 *
 * @example
 * ```tsx
 * const { data: canDelete, isLoading } = usePermission({
 *   permission: "Delete",
 *   scope_type: "Flow",
 *   scope_id: flowId
 * });
 *
 * if (canDelete) {
 *   return <Button onClick={handleDelete}>Delete</Button>;
 * }
 * ```
 */
export function usePermission(check: PermissionCheck) {
  return useQuery({
    queryKey: [
      "permission",
      check.permission,
      check.scope_type,
      check.scope_id,
    ],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append("permission", check.permission);
      params.append("scope_type", check.scope_type);
      if (check.scope_id) {
        params.append("scope_id", check.scope_id);
      }

      const response = await api.get(
        `/api/v1/rbac/check-permission?${params.toString()}`,
      );
      return response.data.has_permission as boolean;
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
}

/**
 * Hook to check multiple permissions in a single request.
 * More efficient than multiple individual permission checks.
 *
 * @param checks - Array of permission checks
 * @returns Query result with results object mapping check keys to boolean values
 *
 * @example
 * ```tsx
 * const { data: permissions } = useBatchPermissions([
 *   { permission: "Update", scope_type: "Flow", scope_id: flowId },
 *   { permission: "Delete", scope_type: "Flow", scope_id: flowId }
 * ]);
 *
 * const canUpdate = permissions?.[0];
 * const canDelete = permissions?.[1];
 * ```
 */
export function useBatchPermissions(checks: PermissionCheck[]) {
  return useQuery({
    queryKey: ["permissions-batch", checks],
    queryFn: async () => {
      const response = await api.post("/api/v1/rbac/check-permissions", {
        checks,
      });
      return response.data.results as Record<string, boolean>;
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
}

/**
 * Hook to invalidate permission caches when role assignments change.
 * Use this in mutation hooks (create/update/delete assignments).
 *
 * @returns Object with cache invalidation functions
 *
 * @example
 * ```tsx
 * const invalidatePermissions = useInvalidatePermissions();
 *
 * const deleteMutation = useMutation({
 *   mutationFn: deleteAssignment,
 *   onSuccess: () => {
 *     // Invalidate all permission caches when assignment is deleted
 *     invalidatePermissions.invalidateAll();
 *   }
 * });
 * ```
 */
export function useInvalidatePermissions() {
  const queryClient = useQueryClient();

  return {
    /**
     * Invalidate all permission queries.
     * Use when assignments are deleted or when global changes occur.
     */
    invalidateAll: () => {
      queryClient.invalidateQueries({ queryKey: ["permission"] });
      queryClient.invalidateQueries({ queryKey: ["permissions-batch"] });
    },

    /**
     * Invalidate permission queries for a specific user.
     * Use when a user's role assignments are created or updated.
     *
     * @param userId - The user ID whose permissions changed
     */
    invalidateForUser: (userId: string) => {
      // Invalidate all permission queries since we don't track user-specific queries
      queryClient.invalidateQueries({ queryKey: ["permission"] });
      queryClient.invalidateQueries({ queryKey: ["permissions-batch"] });
    },

    /**
     * Invalidate permission queries for a specific resource.
     * Use when resource-specific role assignments change.
     *
     * @param scopeType - The resource type (e.g., "Flow", "Project")
     * @param scopeId - The resource ID
     */
    invalidateForResource: (scopeType: string, scopeId: string) => {
      // Invalidate permission queries matching the scope
      queryClient.invalidateQueries({
        queryKey: ["permission"],
        predicate: (query) => {
          const key = query.queryKey;
          return key[2] === scopeType && key[3] === scopeId;
        },
      });
    },
  };
}
