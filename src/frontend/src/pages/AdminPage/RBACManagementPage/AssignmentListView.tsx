import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import IconComponent from "@/components/common/genericIconComponent";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/controllers/API";
import CustomLoader from "@/customization/components/custom-loader";
import useAlertStore from "@/stores/alertStore";

interface Assignment {
  id: string;
  user_id: string;
  username?: string;
  role_name: string;
  scope_type: string;
  scope_id: string | null;
  scope_name: string | null;
  is_immutable: boolean;
  created_at: string;
}

interface AssignmentListViewProps {
  onEditAssignment: (id: string) => void;
}

export default function AssignmentListView({
  onEditAssignment,
}: AssignmentListViewProps) {
  const queryClient = useQueryClient();
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  const [filters, setFilters] = useState({
    username: "",
    role_name: "",
    scope_type: "",
  });

  // Fetch assignments with filters
  const {
    data: assignments = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ["rbac-assignments", filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.username) params.append("username", filters.username);
      if (filters.role_name) params.append("role_name", filters.role_name);
      if (filters.scope_type) params.append("scope_type", filters.scope_type);

      const response = await api.get(
        `/api/v1/rbac/assignments?${params.toString()}`,
      );
      return response.data as Assignment[];
    },
    staleTime: 30000, // Cache for 30 seconds
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (assignmentId: string) => {
      await api.delete(`/api/v1/rbac/assignments/${assignmentId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rbac-assignments"] });
      setSuccessData({ title: "Role assignment deleted successfully" });
    },
    onError: (error: any) => {
      setErrorData({
        title: "Failed to delete role assignment",
        list: [
          error?.response?.data?.detail ||
            error?.message ||
            "An error occurred",
        ],
      });
    },
  });

  const handleFilterChange = (field: string, value: string) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
  };

  const clearFilter = (field: string) => {
    setFilters((prev) => ({ ...prev, [field]: "" }));
  };

  // Client-side filtering is handled by query key changes
  // Use assignments directly since filtering is done via API
  const filteredAssignments = assignments;

  const handleDelete = async (assignment: Assignment) => {
    if (assignment.is_immutable) {
      setErrorData({
        title: "Cannot delete immutable assignment",
        list: [
          "This is a system-managed assignment (e.g., Starter Project Owner) and cannot be deleted.",
        ],
      });
      return;
    }

    if (
      window.confirm(
        `Delete ${assignment.role_name} assignment for ${assignment.username || assignment.user_id}?`,
      )
    ) {
      await deleteMutation.mutateAsync(assignment.id);
    }
  };

  // Show error alert if query fails
  if (error) {
    setErrorData({
      title: "Failed to load role assignments",
      list: [
        (error as any)?.response?.data?.detail ||
          (error as any)?.message ||
          "An error occurred while fetching role assignments",
      ],
    });
  }

  return (
    <div className="flex flex-col space-y-4">
      <div className="flex gap-4">
        <div className="flex w-64 items-center gap-2">
          <Input
            placeholder="Filter by username..."
            value={filters.username}
            onChange={(e) => handleFilterChange("username", e.target.value)}
          />
          {filters.username.length > 0 && (
            <div
              className="cursor-pointer"
              onClick={() => clearFilter("username")}
            >
              <IconComponent name="X" className="h-4 w-4 text-foreground" />
            </div>
          )}
        </div>
        <div className="flex w-64 items-center gap-2">
          <Input
            placeholder="Filter by role..."
            value={filters.role_name}
            onChange={(e) => handleFilterChange("role_name", e.target.value)}
          />
          {filters.role_name.length > 0 && (
            <div
              className="cursor-pointer"
              onClick={() => clearFilter("role_name")}
            >
              <IconComponent name="X" className="h-4 w-4 text-foreground" />
            </div>
          )}
        </div>
        <div className="flex w-64 items-center gap-2">
          <Input
            placeholder="Filter by scope..."
            value={filters.scope_type}
            onChange={(e) => handleFilterChange("scope_type", e.target.value)}
          />
          {filters.scope_type.length > 0 && (
            <div
              className="cursor-pointer"
              onClick={() => clearFilter("scope_type")}
            >
              <IconComponent name="X" className="h-4 w-4 text-foreground" />
            </div>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <CustomLoader remSize={8} />
        </div>
      ) : filteredAssignments.length === 0 ? (
        <div className="flex h-64 items-center justify-center rounded-md border border-border bg-muted/20">
          <div className="text-center">
            <IconComponent
              name="UserCog"
              className="mx-auto h-12 w-12 text-muted-foreground"
            />
            <p className="mt-2 text-sm text-muted-foreground">
              {assignments.length === 0
                ? "No role assignments found. Create your first assignment."
                : "No assignments match your filters."}
            </p>
          </div>
        </div>
      ) : (
        <div className="rounded-md border border-border bg-background">
          <Table>
            <TableHeader className="bg-muted">
              <TableRow>
                <TableHead className="h-10">Username</TableHead>
                <TableHead className="h-10">Role</TableHead>
                <TableHead className="h-10">Scope Type</TableHead>
                <TableHead className="h-10">Scope Name</TableHead>
                <TableHead className="h-10">Created At</TableHead>
                <TableHead className="h-10 w-[100px] text-right">
                  Actions
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAssignments.map((assignment) => (
                <TableRow key={assignment.id}>
                  <TableCell className="py-2 font-medium">
                    {assignment.username || assignment.user_id}
                  </TableCell>
                  <TableCell className="py-2">{assignment.role_name}</TableCell>
                  <TableCell className="py-2 capitalize">
                    {assignment.scope_type}
                  </TableCell>
                  <TableCell className="py-2">
                    {assignment.scope_name || "-"}
                  </TableCell>
                  <TableCell className="py-2">
                    {
                      new Date(assignment.created_at)
                        .toISOString()
                        .split("T")[0]
                    }
                  </TableCell>
                  <TableCell className="py-2 text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onEditAssignment(assignment.id)}
                        disabled={assignment.is_immutable}
                      >
                        <IconComponent name="Pencil" className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(assignment)}
                        disabled={
                          assignment.is_immutable || deleteMutation.isPending
                        }
                      >
                        <IconComponent name="Trash2" className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
