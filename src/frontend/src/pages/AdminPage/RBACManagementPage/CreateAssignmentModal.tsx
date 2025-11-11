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
  const [userId, setUserId] = useState("");
  const [roleName, setRoleName] = useState("");
  const [scopeType, setScopeType] = useState("");
  const [scopeId, setScopeId] = useState("");

  const handleSubmit = () => {
    // TODO: Implement API call to create assignment
    console.log("Creating assignment:", {
      userId,
      roleName,
      scopeType,
      scopeId,
    });
    onSuccess();
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
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit}>Create Assignment</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
