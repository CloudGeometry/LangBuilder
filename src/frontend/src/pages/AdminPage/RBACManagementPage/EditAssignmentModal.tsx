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
  const [roleName, setRoleName] = useState("");
  const [scopeType, setScopeType] = useState("");
  const [scopeId, setScopeId] = useState("");

  useEffect(() => {
    if (open && assignmentId) {
      // TODO: Fetch assignment details
      console.log("Fetching assignment:", assignmentId);
    }
  }, [open, assignmentId]);

  const handleSubmit = () => {
    // TODO: Implement API call to update assignment
    console.log("Updating assignment:", {
      assignmentId,
      roleName,
      scopeType,
      scopeId,
    });
    onSuccess();
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
        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit}>Save Changes</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
