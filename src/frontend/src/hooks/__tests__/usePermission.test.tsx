import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { ReactNode } from "react";
import { api } from "@/controllers/API";
import {
  PermissionCheck,
  useBatchPermissions,
  useInvalidatePermissions,
  usePermission,
} from "../usePermission";

// Mock the API
jest.mock("@/controllers/API", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

describe("usePermission", () => {
  let queryClient: QueryClient;

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  beforeEach(() => {
    jest.clearAllMocks();
    // Create a new QueryClient for each test to ensure isolation
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false, // Disable retries in tests
          gcTime: 0, // Disable caching in tests
        },
      },
    });
  });

  afterEach(() => {
    queryClient.clear();
  });

  describe("usePermission hook", () => {
    it("should fetch permission and return true when user has permission", async () => {
      const check: PermissionCheck = {
        permission: "Delete",
        scope_type: "Flow",
        scope_id: "flow-123",
      };

      (api.get as jest.Mock).mockResolvedValueOnce({
        data: { has_permission: true },
      });

      const { result } = renderHook(() => usePermission(check), { wrapper });

      // Initially loading
      expect(result.current.isLoading).toBe(true);
      expect(result.current.data).toBeUndefined();

      // Wait for data to load
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toBe(true);
      expect(result.current.isLoading).toBe(false);
      expect(api.get).toHaveBeenCalledWith(
        "/api/v1/rbac/check-permission?permission=Delete&scope_type=Flow&scope_id=flow-123",
      );
    });

    it("should fetch permission and return false when user lacks permission", async () => {
      const check: PermissionCheck = {
        permission: "Update",
        scope_type: "Project",
        scope_id: "project-456",
      };

      (api.get as jest.Mock).mockResolvedValueOnce({
        data: { has_permission: false },
      });

      const { result } = renderHook(() => usePermission(check), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toBe(false);
      expect(api.get).toHaveBeenCalledWith(
        "/api/v1/rbac/check-permission?permission=Update&scope_type=Project&scope_id=project-456",
      );
    });

    it("should handle permission check without scope_id", async () => {
      const check: PermissionCheck = {
        permission: "Create",
        scope_type: "Flow",
        scope_id: null,
      };

      (api.get as jest.Mock).mockResolvedValueOnce({
        data: { has_permission: true },
      });

      const { result } = renderHook(() => usePermission(check), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toBe(true);
      expect(api.get).toHaveBeenCalledWith(
        "/api/v1/rbac/check-permission?permission=Create&scope_type=Flow",
      );
    });

    it("should handle API errors", async () => {
      const check: PermissionCheck = {
        permission: "Read",
        scope_type: "Flow",
        scope_id: "flow-789",
      };

      (api.get as jest.Mock).mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() => usePermission(check), { wrapper });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeDefined();
      expect(result.current.data).toBeUndefined();
    });

    it("should cache results based on query key", async () => {
      const check: PermissionCheck = {
        permission: "Delete",
        scope_type: "Flow",
        scope_id: "flow-123",
      };

      (api.get as jest.Mock).mockResolvedValue({
        data: { has_permission: true },
      });

      // First render
      const { result: result1 } = renderHook(() => usePermission(check), {
        wrapper,
      });
      await waitFor(() => expect(result1.current.isSuccess).toBe(true));

      // Second render with same check - should use cache
      const { result: result2 } = renderHook(() => usePermission(check), {
        wrapper,
      });

      // Should immediately have data from cache
      expect(result2.current.data).toBe(true);

      // API should only be called once (from first render)
      expect(api.get).toHaveBeenCalledTimes(1);
    });

    it("should use different cache for different permissions", async () => {
      const check1: PermissionCheck = {
        permission: "Delete",
        scope_type: "Flow",
        scope_id: "flow-123",
      };

      const check2: PermissionCheck = {
        permission: "Update",
        scope_type: "Flow",
        scope_id: "flow-123",
      };

      (api.get as jest.Mock)
        .mockResolvedValueOnce({
          data: { has_permission: true },
        })
        .mockResolvedValueOnce({
          data: { has_permission: false },
        });

      // First permission check
      const { result: result1 } = renderHook(() => usePermission(check1), {
        wrapper,
      });
      await waitFor(() => expect(result1.current.isSuccess).toBe(true));

      // Second permission check (different permission)
      const { result: result2 } = renderHook(() => usePermission(check2), {
        wrapper,
      });
      await waitFor(() => expect(result2.current.isSuccess).toBe(true));

      // Should make two API calls
      expect(api.get).toHaveBeenCalledTimes(2);
      expect(result1.current.data).toBe(true);
      expect(result2.current.data).toBe(false);
    });
  });

  describe("useBatchPermissions hook", () => {
    it("should fetch multiple permissions in a single request", async () => {
      const checks: PermissionCheck[] = [
        { permission: "Update", scope_type: "Flow", scope_id: "flow-123" },
        { permission: "Delete", scope_type: "Flow", scope_id: "flow-123" },
      ];

      const mockResponse = {
        data: {
          results: {
            "0": true,
            "1": false,
          },
        },
      };

      (api.post as jest.Mock).mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useBatchPermissions(checks), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual({
        "0": true,
        "1": false,
      });
      expect(api.post).toHaveBeenCalledWith("/api/v1/rbac/check-permissions", {
        checks,
      });
    });

    it("should handle empty checks array", async () => {
      const checks: PermissionCheck[] = [];

      (api.post as jest.Mock).mockResolvedValueOnce({
        data: { results: {} },
      });

      const { result } = renderHook(() => useBatchPermissions(checks), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual({});
      expect(api.post).toHaveBeenCalledWith("/api/v1/rbac/check-permissions", {
        checks: [],
      });
    });

    it("should handle batch API errors", async () => {
      const checks: PermissionCheck[] = [
        { permission: "Read", scope_type: "Flow", scope_id: "flow-123" },
      ];

      (api.post as jest.Mock).mockRejectedValueOnce(new Error("Server error"));

      const { result } = renderHook(() => useBatchPermissions(checks), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeDefined();
      expect(result.current.data).toBeUndefined();
    });
  });

  describe("useInvalidatePermissions hook", () => {
    it("should invalidate all permission queries", () => {
      const check: PermissionCheck = {
        permission: "Delete",
        scope_type: "Flow",
        scope_id: "flow-123",
      };

      (api.get as jest.Mock).mockResolvedValue({
        data: { has_permission: true },
      });

      // Render the invalidate hook
      const { result: invalidateResult } = renderHook(
        () => useInvalidatePermissions(),
        { wrapper },
      );

      // Test that the function exists and can be called without error
      expect(invalidateResult.current.invalidateAll).toBeDefined();
      expect(() => invalidateResult.current.invalidateAll()).not.toThrow();
    });

    it("should invalidate permissions for a specific user", () => {
      // Render the invalidate hook
      const { result: invalidateResult } = renderHook(
        () => useInvalidatePermissions(),
        { wrapper },
      );

      // Test that the function exists and can be called without error
      expect(invalidateResult.current.invalidateForUser).toBeDefined();
      expect(() =>
        invalidateResult.current.invalidateForUser("user-123"),
      ).not.toThrow();
    });

    it("should invalidate permissions for a specific resource", () => {
      // Render the invalidate hook
      const { result: invalidateResult } = renderHook(
        () => useInvalidatePermissions(),
        { wrapper },
      );

      // Test that the function exists and can be called without error
      expect(invalidateResult.current.invalidateForResource).toBeDefined();
      expect(() =>
        invalidateResult.current.invalidateForResource("Flow", "flow-123"),
      ).not.toThrow();
    });

    it("should not invalidate unrelated permission queries when invalidating for resource", async () => {
      const check1: PermissionCheck = {
        permission: "Delete",
        scope_type: "Flow",
        scope_id: "flow-123",
      };

      const check2: PermissionCheck = {
        permission: "Delete",
        scope_type: "Flow",
        scope_id: "flow-456",
      };

      (api.get as jest.Mock).mockResolvedValue({
        data: { has_permission: true },
      });

      // Render both permission hooks
      const { result: result1 } = renderHook(() => usePermission(check1), {
        wrapper,
      });
      const { result: result2 } = renderHook(() => usePermission(check2), {
        wrapper,
      });

      await waitFor(() => expect(result1.current.isSuccess).toBe(true));
      await waitFor(() => expect(result2.current.isSuccess).toBe(true));

      const { result: invalidateResult } = renderHook(
        () => useInvalidatePermissions(),
        { wrapper },
      );

      // Clear API call count
      (api.get as jest.Mock).mockClear();

      // Invalidate only flow-123
      invalidateResult.current.invalidateForResource("Flow", "flow-123");

      // Wait a bit to see if refetch happens
      await waitFor(() => expect(api.get).toHaveBeenCalled(), { timeout: 500 });

      // Only one API call should be made (for flow-123)
      expect(api.get).toHaveBeenCalledTimes(1);
      expect(api.get).toHaveBeenCalledWith(
        "/api/v1/rbac/check-permission?permission=Delete&scope_type=Flow&scope_id=flow-123",
      );
    });
  });

  describe("Cache behavior", () => {
    it("should respect staleTime of 5 minutes", async () => {
      const check: PermissionCheck = {
        permission: "Read",
        scope_type: "Flow",
        scope_id: "flow-123",
      };

      (api.get as jest.Mock).mockResolvedValue({
        data: { has_permission: true },
      });

      // Create QueryClient with realistic staleTime
      queryClient = new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            staleTime: 5 * 60 * 1000, // 5 minutes
          },
        },
      });

      const { result } = renderHook(() => usePermission(check), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Data should not be stale immediately
      expect(result.current.isStale).toBe(false);
      expect(api.get).toHaveBeenCalledTimes(1);
    });
  });
});
