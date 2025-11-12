import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { ReactNode } from "react";
import { api } from "@/controllers/API";
import {
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

describe("usePermission hook", () => {
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

  describe("usePermission", () => {
    it("should call API with correct parameters", async () => {
      const mockResponse = { data: { has_permission: true } };
      (api.get as jest.Mock).mockResolvedValue(mockResponse);

      const { result } = renderHook(
        () =>
          usePermission({
            permission: "Delete",
            scope_type: "Flow",
            scope_id: "flow-123",
          }),
        { wrapper },
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.get).toHaveBeenCalledWith(
        "/api/v1/rbac/check-permission?permission=Delete&scope_type=Flow&scope_id=flow-123",
      );
      expect(result.current.data).toBe(true);
    });

    it("should call API without scope_id when not provided", async () => {
      const mockResponse = { data: { has_permission: false } };
      (api.get as jest.Mock).mockResolvedValue(mockResponse);

      const { result } = renderHook(
        () =>
          usePermission({
            permission: "Create",
            scope_type: "Project",
            scope_id: null,
          }),
        { wrapper },
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.get).toHaveBeenCalledWith(
        "/api/v1/rbac/check-permission?permission=Create&scope_type=Project",
      );
      expect(result.current.data).toBe(false);
    });

    it("should return permission denied when API returns false", async () => {
      const mockResponse = { data: { has_permission: false } };
      (api.get as jest.Mock).mockResolvedValue(mockResponse);

      const { result } = renderHook(
        () =>
          usePermission({
            permission: "Update",
            scope_type: "Flow",
            scope_id: "flow-456",
          }),
        { wrapper },
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toBe(false);
    });

    it("should cache results for 5 minutes (staleTime)", async () => {
      const mockResponse = { data: { has_permission: true } };
      (api.get as jest.Mock).mockResolvedValue(mockResponse);

      const { result: result1 } = renderHook(
        () =>
          usePermission({
            permission: "Read",
            scope_type: "Flow",
            scope_id: "flow-789",
          }),
        { wrapper },
      );

      await waitFor(() => {
        expect(result1.current.isSuccess).toBe(true);
      });

      // Call hook again with same parameters
      const { result: result2 } = renderHook(
        () =>
          usePermission({
            permission: "Read",
            scope_type: "Flow",
            scope_id: "flow-789",
          }),
        { wrapper },
      );

      await waitFor(() => {
        expect(result2.current.isSuccess).toBe(true);
      });

      // API should only be called once due to caching
      expect(api.get).toHaveBeenCalledTimes(1);
      expect(result2.current.data).toBe(true);
    });

    it("should handle API errors gracefully", async () => {
      const mockError = new Error("Network error");
      (api.get as jest.Mock).mockRejectedValue(mockError);

      const { result } = renderHook(
        () =>
          usePermission({
            permission: "Delete",
            scope_type: "Flow",
            scope_id: "flow-error",
          }),
        { wrapper },
      );

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.data).toBeUndefined();
    });

    it("should use correct query key for caching", async () => {
      const mockResponse = { data: { has_permission: true } };
      (api.get as jest.Mock).mockResolvedValue(mockResponse);

      const { result } = renderHook(
        () =>
          usePermission({
            permission: "Update",
            scope_type: "Project",
            scope_id: "project-123",
          }),
        { wrapper },
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Verify query is cached with correct key
      const cachedData = queryClient.getQueryData([
        "permission",
        "Update",
        "Project",
        "project-123",
      ]);
      expect(cachedData).toBe(true);
    });
  });

  describe("useBatchPermissions", () => {
    it("should call batch API with multiple permission checks", async () => {
      const mockResponse = {
        data: {
          results: {
            "0": true,
            "1": false,
            "2": true,
          },
        },
      };
      (api.post as jest.Mock).mockResolvedValue(mockResponse);

      const checks = [
        { permission: "Update", scope_type: "Flow", scope_id: "flow-1" },
        { permission: "Delete", scope_type: "Flow", scope_id: "flow-1" },
        { permission: "Create", scope_type: "Project", scope_id: null },
      ];

      const { result } = renderHook(() => useBatchPermissions(checks), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.post).toHaveBeenCalledWith("/api/v1/rbac/check-permissions", {
        checks,
      });
      expect(result.current.data).toEqual({
        "0": true,
        "1": false,
        "2": true,
      });
    });

    it("should cache batch permission results", async () => {
      const mockResponse = {
        data: {
          results: { "0": true, "1": false },
        },
      };
      (api.post as jest.Mock).mockResolvedValue(mockResponse);

      const checks = [
        { permission: "Update", scope_type: "Flow", scope_id: "flow-1" },
        { permission: "Delete", scope_type: "Flow", scope_id: "flow-1" },
      ];

      const { result: result1 } = renderHook(
        () => useBatchPermissions(checks),
        { wrapper },
      );

      await waitFor(() => {
        expect(result1.current.isSuccess).toBe(true);
      });

      // Call again with same checks
      const { result: result2 } = renderHook(
        () => useBatchPermissions(checks),
        { wrapper },
      );

      await waitFor(() => {
        expect(result2.current.isSuccess).toBe(true);
      });

      // API should only be called once
      expect(api.post).toHaveBeenCalledTimes(1);
    });

    it("should handle batch API errors", async () => {
      const mockError = new Error("Batch check failed");
      (api.post as jest.Mock).mockRejectedValue(mockError);

      const checks = [
        { permission: "Update", scope_type: "Flow", scope_id: "flow-1" },
      ];

      const { result } = renderHook(() => useBatchPermissions(checks), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeTruthy();
    });
  });

  describe("useInvalidatePermissions", () => {
    it("should invalidate all permission queries", async () => {
      const mockResponse = { data: { has_permission: true } };
      (api.get as jest.Mock).mockResolvedValue(mockResponse);

      // First, populate some permission caches
      const { result: permission1 } = renderHook(
        () =>
          usePermission({
            permission: "Update",
            scope_type: "Flow",
            scope_id: "flow-1",
          }),
        { wrapper },
      );

      await waitFor(() => {
        expect(permission1.current.isSuccess).toBe(true);
      });

      // Get invalidation functions
      const { result: invalidate } = renderHook(
        () => useInvalidatePermissions(),
        { wrapper },
      );

      // Invalidate all
      invalidate.current.invalidateAll();

      // Query should be marked as stale
      const queryState = queryClient.getQueryState([
        "permission",
        "Update",
        "Flow",
        "flow-1",
      ]);
      expect(queryState?.isInvalidated).toBe(true);
    });

    it("should invalidate permissions for a specific user", async () => {
      const mockResponse = { data: { has_permission: true } };
      (api.get as jest.Mock).mockResolvedValue(mockResponse);

      const { result: permission1 } = renderHook(
        () =>
          usePermission({
            permission: "Delete",
            scope_type: "Flow",
            scope_id: "flow-1",
          }),
        { wrapper },
      );

      await waitFor(() => {
        expect(permission1.current.isSuccess).toBe(true);
      });

      const { result: invalidate } = renderHook(
        () => useInvalidatePermissions(),
        { wrapper },
      );

      // Invalidate for specific user (invalidates all since we don't track user-specific)
      invalidate.current.invalidateForUser("user-123");

      const queryState = queryClient.getQueryState([
        "permission",
        "Delete",
        "Flow",
        "flow-1",
      ]);
      expect(queryState?.isInvalidated).toBe(true);
    });

    it("should invalidate permissions for a specific resource", async () => {
      const mockResponse = { data: { has_permission: true } };
      (api.get as jest.Mock).mockResolvedValue(mockResponse);

      // Create two permission queries
      const { result: permission1 } = renderHook(
        () =>
          usePermission({
            permission: "Update",
            scope_type: "Flow",
            scope_id: "flow-1",
          }),
        { wrapper },
      );

      const { result: permission2 } = renderHook(
        () =>
          usePermission({
            permission: "Delete",
            scope_type: "Flow",
            scope_id: "flow-2",
          }),
        { wrapper },
      );

      await waitFor(() => {
        expect(permission1.current.isSuccess).toBe(true);
        expect(permission2.current.isSuccess).toBe(true);
      });

      const { result: invalidate } = renderHook(
        () => useInvalidatePermissions(),
        { wrapper },
      );

      // Invalidate only flow-1
      invalidate.current.invalidateForResource("Flow", "flow-1");

      // flow-1 query should be invalidated
      const queryState1 = queryClient.getQueryState([
        "permission",
        "Update",
        "Flow",
        "flow-1",
      ]);
      expect(queryState1?.isInvalidated).toBe(true);

      // flow-2 query should NOT be invalidated
      const queryState2 = queryClient.getQueryState([
        "permission",
        "Delete",
        "Flow",
        "flow-2",
      ]);
      expect(queryState2?.isInvalidated).toBe(false);
    });
  });
});
