import { useState } from "react";
import IconComponent from "@/components/common/genericIconComponent";
import { Button } from "@/components/ui/button";
import AssignmentListView from "./AssignmentListView";
import CreateAssignmentModal from "./CreateAssignmentModal";
import EditAssignmentModal from "./EditAssignmentModal";

export default function RBACManagementPage() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<
    string | null
  >(null);

  const handleEditAssignment = (id: string) => {
    setSelectedAssignmentId(id);
    setIsEditModalOpen(true);
  };

  const handleCloseEditModal = () => {
    setIsEditModalOpen(false);
    setSelectedAssignmentId(null);
  };

  const handleSuccessCreate = () => {
    setIsCreateModalOpen(false);
  };

  const handleSuccessEdit = () => {
    setIsEditModalOpen(false);
    setSelectedAssignmentId(null);
  };

  return (
    <div className="flex h-full flex-col space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            Role-Based Access Control
          </h2>
          <p className="text-muted-foreground">
            Manage role assignments for users across projects and flows
          </p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <IconComponent name="Plus" className="mr-2 h-4 w-4" />
          New Assignment
        </Button>
      </div>

      <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/50 p-4">
        <IconComponent name="Info" className="h-5 w-5 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          Project-level assignments are inherited by contained Flows and can be
          overridden by explicit Flow-specific roles.
        </span>
      </div>

      <AssignmentListView onEditAssignment={handleEditAssignment} />

      <CreateAssignmentModal
        open={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleSuccessCreate}
      />

      {selectedAssignmentId && (
        <EditAssignmentModal
          open={isEditModalOpen}
          assignmentId={selectedAssignmentId}
          onClose={handleCloseEditModal}
          onSuccess={handleSuccessEdit}
        />
      )}
    </div>
  );
}
