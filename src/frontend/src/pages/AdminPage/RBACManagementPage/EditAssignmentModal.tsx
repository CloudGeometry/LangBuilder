import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/controllers/API";
import CustomLoader from "@/customization/components/custom-loader";
import useAlertStore from "@/stores/alertStore";

interface EditAssignmentModalProps {
  open: boolean;
  assignmentId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function EditAssignmentModal({
  open,
  assignmentId,
  onClose,
  onSuccess,
}: EditAssignmentModalProps) {
  const queryClient = useQueryClient();
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  const [roleName, setRoleName] = useState("");
  const [scopeType, setScopeType] = useState("");
  const [scopeId, setScopeId] = useState("");

  // Fetch assignment details
  const { data: assignment, isLoading: isLoadingAssignment } = useQuery({
    queryKey: ["rbac-assignment", assignmentId],
    queryFn: async () => {
      const response = await api.get(
        `/api/v1/rbac/assignments/${assignmentId}`,
      );
      return response.data;
    },
    enabled: open && !!assignmentId,
  });

  // Populate form when data loads
  useEffect(() => {
    if (assignment) {
      setRoleName(assignment.role_name || "");
      setScopeType(assignment.scope_type || "");
      setScopeId(assignment.scope_id || "");
    }
  }, [assignment]);

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: async (updateData: any) => {
      const response = await api.patch(
        `/api/v1/rbac/assignments/${assignmentId}`,
        updateData,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rbac-assignments"] });
      queryClient.invalidateQueries({
        queryKey: ["rbac-assignment", assignmentId],
      });
      setSuccessData({ title: "Role assignment updated successfully" });
      handleClose();
      onSuccess();
    },
    onError: (error: any) => {
      setErrorData({
        title: "Failed to update role assignment",
        list: [
          error?.response?.data?.detail ||
            error?.message ||
            "An error occurred",
        ],
      });
    },
  });

  const handleSubmit = () => {
    // Validate required fields
    if (!roleName || !scopeType) {
      setErrorData({
        title: "Validation Error",
        list: ["Role and Scope Type are required"],
      });
      return;
    }

    // Validate scope_id for non-Global scopes
    if (scopeType !== "Global" && !scopeId) {
      setErrorData({
        title: "Validation Error",
        list: ["Scope ID is required for Project and Flow scopes"],
      });
      return;
    }

    // Validate scope_id should be empty for Global scope
    if (scopeType === "Global" && scopeId) {
      setErrorData({
        title: "Validation Error",
        list: ["Scope ID should be empty for Global scope"],
      });
      return;
    }

    updateMutation.mutate({
      role_name: roleName,
      scope_type: scopeType,
      scope_id: scopeId || null,
    });
  };

  const handleClose = () => {
    setRoleName("");
    setScopeType("");
    setScopeId("");
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Role Assignment</DialogTitle>
          <DialogDescription>
            Update the role assignment details. User cannot be changed.
          </DialogDescription>
        </DialogHeader>
        {isLoadingAssignment ? (
          <div className="flex items-center justify-center py-8">
            <CustomLoader remSize={4} />
          </div>
        ) : (
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="roleName">Role</Label>
              <Input
                id="roleName"
                placeholder="Select role..."
                value={roleName}
                onChange={(e) => setRoleName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="scopeType">Scope Type</Label>
              <Input
                id="scopeType"
                placeholder="Select scope type..."
                value={scopeType}
                onChange={(e) => setScopeType(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="scopeId">Scope ID (optional)</Label>
              <Input
                id="scopeId"
                placeholder="Enter scope ID..."
                value={scopeId}
                onChange={(e) => setScopeId(e.target.value)}
              />
            </div>
          </div>
        )}
        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={updateMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={updateMutation.isPending || isLoadingAssignment}
          >
            {updateMutation.isPending ? "Saving..." : "Save Changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
