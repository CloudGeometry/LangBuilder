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
import CustomLoader from "@/customization/components/custom-loader";

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
  const [filters, setFilters] = useState({
    username: "",
    role_name: "",
    scope_type: "",
  });
  const [isLoading] = useState(false);
  const [assignments] = useState<Assignment[]>([]);

  const handleFilterChange = (field: string, value: string) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
  };

  const clearFilter = (field: string) => {
    setFilters((prev) => ({ ...prev, [field]: "" }));
  };

  const filteredAssignments = assignments.filter((assignment) => {
    const matchesUsername = filters.username
      ? assignment.username
          ?.toLowerCase()
          .includes(filters.username.toLowerCase())
      : true;
    const matchesRole = filters.role_name
      ? assignment.role_name
          .toLowerCase()
          .includes(filters.role_name.toLowerCase())
      : true;
    const matchesScope = filters.scope_type
      ? assignment.scope_type
          .toLowerCase()
          .includes(filters.scope_type.toLowerCase())
      : true;
    return matchesUsername && matchesRole && matchesScope;
  });

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
                        disabled={assignment.is_immutable}
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
