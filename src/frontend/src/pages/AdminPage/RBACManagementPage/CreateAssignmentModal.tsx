import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/controllers/API";
import CustomLoader from "@/customization/components/custom-loader";
import useAlertStore from "@/stores/alertStore";

interface CreateAssignmentModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface User {
  id: string;
  username: string;
}

interface Folder {
  id: string;
  name: string;
}

interface Flow {
  id: string;
  name: string;
}

export default function CreateAssignmentModal({
  open,
  onClose,
  onSuccess,
}: CreateAssignmentModalProps) {
  const queryClient = useQueryClient();
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    user_id: "",
    scope_type: "",
    scope_id: "",
    role_name: "",
  });

  // Fetch users for step 1
  const { data: users, isLoading: isLoadingUsers } = useQuery<User[]>({
    queryKey: ["users"],
    queryFn: async () => {
      const response = await api.get("/api/v1/users");
      return response.data;
    },
    enabled: open,
  });

  // Fetch folders (projects) for step 3 when scope is Project
  const { data: folders, isLoading: isLoadingFolders } = useQuery<Folder[]>({
    queryKey: ["folders"],
    queryFn: async () => {
      const response = await api.get("/api/v1/folders");
      return response.data;
    },
    enabled: open && formData.scope_type === "Project",
  });

  // Fetch flows for step 3 when scope is Flow
  const { data: flows, isLoading: isLoadingFlows } = useQuery<Flow[]>({
    queryKey: ["flows"],
    queryFn: async () => {
      const response = await api.get("/api/v1/flows");
      return response.data;
    },
    enabled: open && formData.scope_type === "Flow",
  });

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

  const resetForm = () => {
    setStep(1);
    setFormData({ user_id: "", scope_type: "", scope_id: "", role_name: "" });
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  /**
   * Validates whether the user can proceed from the current step of the wizard.
   *
   * Each step has specific validation requirements:
   * - Step 1 (User Selection): Requires user_id to be selected
   * - Step 2 (Scope Type): Requires scope_type to be selected
   * - Step 3 (Resource Selection): Requires scope_id (automatically passes for Global scope)
   * - Step 4 (Role Selection): Requires role_name to be selected
   *
   * @param currentStep - The current step number (1-4)
   * @returns true if all required fields for the step are filled, false otherwise
   *
   * @example
   * ```typescript
   * // User selected, can proceed from step 1
   * canProceedFromStep(1) // returns true if formData.user_id is set
   *
   * // Global scope selected, automatically passes step 3
   * canProceedFromStep(3) // returns true if scope_type === "Global"
   * ```
   */
  const canProceedFromStep = (currentStep: number): boolean => {
    switch (currentStep) {
      case 1:
        return !!formData.user_id;
      case 2:
        return !!formData.scope_type;
      case 3:
        // For Global scope, skip to step 4
        if (formData.scope_type === "Global") {
          return true;
        }
        // For Project/Flow scope, need scope_id
        return !!formData.scope_id;
      case 4:
        return !!formData.role_name;
      default:
        return false;
    }
  };

  const handleNext = () => {
    // For Global scope, skip step 3 (resource selection)
    if (step === 2 && formData.scope_type === "Global") {
      setStep(4);
    } else if (step < 4) {
      setStep(step + 1);
    }
  };

  const handleBack = () => {
    // For Global scope, skip step 3 (resource selection) when going back
    if (step === 4 && formData.scope_type === "Global") {
      setStep(2);
    } else if (step > 1) {
      setStep(step - 1);
    }
  };

  const handleSubmit = () => {
    createMutation.mutate({
      user_id: formData.user_id,
      role_name: formData.role_name,
      scope_type: formData.scope_type,
      scope_id: formData.scope_type === "Global" ? null : formData.scope_id,
    });
  };

  /**
   * Returns the display title for the current wizard step.
   *
   * @param currentStep - The current step number (1-4)
   * @returns The user-friendly title for the step
   */
  const getStepTitle = (currentStep: number): string => {
    switch (currentStep) {
      case 1:
        return "Select User";
      case 2:
        return "Select Scope Type";
      case 3:
        return `Select ${formData.scope_type}`;
      case 4:
        return "Select Role";
      default:
        return "";
    }
  };

  /**
   * Renders the content for the current wizard step.
   *
   * Each step displays different UI elements:
   * - Step 1: User selection dropdown (loads users from API)
   * - Step 2: Scope type selection (Global, Project, or Flow)
   * - Step 3: Resource selection (Project or Flow, skipped for Global scope)
   * - Step 4: Role selection (Admin for Global, Owner/Editor/Viewer for Project/Flow)
   *
   * Loading states are shown while data is being fetched from the API.
   *
   * @returns React element for the current step, or null if step is invalid
   */
  const renderStepContent = () => {
    if (step === 1) {
      if (isLoadingUsers) {
        return (
          <div className="flex items-center justify-center py-8">
            <CustomLoader remSize={4} />
          </div>
        );
      }

      return (
        <div className="space-y-2">
          <Label htmlFor="user">User</Label>
          <Select
            value={formData.user_id}
            onValueChange={(value) =>
              setFormData({ ...formData, user_id: value })
            }
          >
            <SelectTrigger id="user" className="w-full">
              <SelectValue placeholder="Choose a user..." />
            </SelectTrigger>
            <SelectContent>
              {users?.map((user) => (
                <SelectItem key={user.id} value={user.id}>
                  {user.username}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      );
    }

    if (step === 2) {
      return (
        <div className="space-y-2">
          <Label htmlFor="scopeType">Scope Type</Label>
          <Select
            value={formData.scope_type}
            onValueChange={(value) =>
              setFormData({ ...formData, scope_type: value, scope_id: "" })
            }
          >
            <SelectTrigger id="scopeType" className="w-full">
              <SelectValue placeholder="Choose a scope..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Global">Global (Admin only)</SelectItem>
              <SelectItem value="Project">Project</SelectItem>
              <SelectItem value="Flow">Flow</SelectItem>
            </SelectContent>
          </Select>
        </div>
      );
    }

    if (step === 3 && formData.scope_type !== "Global") {
      const isLoading =
        formData.scope_type === "Project" ? isLoadingFolders : isLoadingFlows;
      const resources = formData.scope_type === "Project" ? folders : flows;

      if (isLoading) {
        return (
          <div className="flex items-center justify-center py-8">
            <CustomLoader remSize={4} />
          </div>
        );
      }

      return (
        <div className="space-y-2">
          <Label htmlFor="resource">{formData.scope_type}</Label>
          <Select
            value={formData.scope_id}
            onValueChange={(value) =>
              setFormData({ ...formData, scope_id: value })
            }
          >
            <SelectTrigger id="resource" className="w-full">
              <SelectValue
                placeholder={`Choose a ${formData.scope_type.toLowerCase()}...`}
              />
            </SelectTrigger>
            <SelectContent>
              {resources?.map((resource) => (
                <SelectItem key={resource.id} value={resource.id}>
                  {resource.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      );
    }

    if (step === 4) {
      const availableRoles =
        formData.scope_type === "Global"
          ? [{ value: "Admin", label: "Admin" }]
          : [
              { value: "Owner", label: "Owner" },
              { value: "Editor", label: "Editor" },
              { value: "Viewer", label: "Viewer" },
            ];

      return (
        <div className="space-y-2">
          <Label htmlFor="role">Role</Label>
          <Select
            value={formData.role_name}
            onValueChange={(value) =>
              setFormData({ ...formData, role_name: value })
            }
          >
            <SelectTrigger id="role" className="w-full">
              <SelectValue placeholder="Choose a role..." />
            </SelectTrigger>
            <SelectContent>
              {availableRoles.map((role) => (
                <SelectItem key={role.value} value={role.value}>
                  {role.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      );
    }

    return null;
  };

  /**
   * Calculates the maximum number of steps for the wizard based on scope type.
   * Global scope has 3 steps (skips resource selection), others have 4 steps.
   * Memoized to avoid recalculation on every render.
   */
  const maxSteps = useMemo(() => {
    return formData.scope_type === "Global" ? 3 : 4;
  }, [formData.scope_type]);

  /**
   * Calculates the display step number, accounting for Global scope skipping step 3.
   * For Global scope, step 4 is displayed as step 3.
   * Memoized to avoid recalculation on every render.
   */
  const currentStepNumber = useMemo(() => {
    if (formData.scope_type === "Global" && step === 4) {
      return 3;
    }
    return step;
  }, [formData.scope_type, step]);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create Role Assignment</DialogTitle>
          <DialogDescription>
            Step {currentStepNumber} of {maxSteps}: {getStepTitle(step)}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">{renderStepContent()}</div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={step === 1 || createMutation.isPending}
          >
            Back
          </Button>
          {step < 4 ? (
            <Button
              onClick={handleNext}
              disabled={!canProceedFromStep(step) || createMutation.isPending}
            >
              Next
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={!formData.role_name || createMutation.isPending}
            >
              {createMutation.isPending ? "Creating..." : "Create Assignment"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
