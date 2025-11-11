import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
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
import useAlertStore from "@/stores/alertStore";

interface CreateAssignmentModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function CreateAssignmentModal({
  open,
  onClose,
  onSuccess,
}: CreateAssignmentModalProps) {
  const queryClient = useQueryClient();
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  const [userId, setUserId] = useState("");
  const [roleName, setRoleName] = useState("");
  const [scopeType, setScopeType] = useState("");
  const [scopeId, setScopeId] = useState("");

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async (assignmentData: any) => {
      const response = await api.post(
        "/api/v1/rbac/assignments",
        assignmentData,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rbac-assignments"] });
      setSuccessData({ title: "Role assignment created successfully" });
      handleClose();
      onSuccess();
    },
    onError: (error: any) => {
      setErrorData({
        title: "Failed to create role assignment",
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
    if (!userId || !roleName || !scopeType) {
      setErrorData({
        title: "Validation Error",
        list: ["User ID, Role, and Scope Type are required"],
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

    createMutation.mutate({
      user_id: userId,
      role_name: roleName,
      scope_type: scopeType,
      scope_id: scopeId || null,
    });
  };

  const handleClose = () => {
    setUserId("");
    setRoleName("");
    setScopeType("");
    setScopeId("");
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Role Assignment</DialogTitle>
          <DialogDescription>
            Assign a role to a user for a specific scope (Global, Project, or
            Flow).
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="userId">User ID</Label>
            <Input
              id="userId"
              placeholder="Enter user ID..."
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </div>
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
        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={createMutation.isPending}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating..." : "Create Assignment"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
