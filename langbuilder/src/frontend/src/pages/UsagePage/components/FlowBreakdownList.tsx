import { useState } from "react";
import type { FlowUsage } from "@/types/usage";
import { FlowBreakdownRow } from "./FlowBreakdownRow";

const PAGE_SIZE = 50;

interface DateRange {
  from: string | null;
  to: string | null;
}

interface FlowBreakdownListProps {
  flows: FlowUsage[];
  onFlowExpand: (flowId: string) => void;
  dateRange?: DateRange;
  selectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
}

export function FlowBreakdownList({
  flows,
  onFlowExpand,
  dateRange = { from: null, to: null },
  selectedIds,
  onSelectionChange,
}: FlowBreakdownListProps) {
  const [page, setPage] = useState(0);

  const totalPages = Math.ceil(flows.length / PAGE_SIZE);
  const pageFlows = flows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handlePrev = () => setPage((p) => Math.max(0, p - 1));
  const handleNext = () => setPage((p) => Math.min(totalPages - 1, p + 1));

  if (flows.length === 0) {
    return (
      <div
        data-testid="flow-breakdown-empty"
        className="flex items-center justify-center p-8 text-sm text-muted-foreground"
      >
        No flows found
      </div>
    );
  }

  return (
    <div data-testid="flow-breakdown-list" className="space-y-2">
      <div className="rounded-md border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50 border-b">
              <th className="px-4 py-3 w-10">
                <input
                  type="checkbox"
                  data-testid="select-all-checkbox"
                  checked={selectedIds !== undefined && flows.length > 0 && flows.every(f => selectedIds.has(f.flow_id))}
                  onChange={(e) => {
                    if (!onSelectionChange) return;
                    if (e.target.checked) {
                      onSelectionChange(new Set(flows.map(f => f.flow_id)));
                    } else {
                      onSelectionChange(new Set());
                    }
                  }}
                  className="h-4 w-4 rounded border-border"
                />
              </th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Flow</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Total Cost</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Invocations</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Avg Cost</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground" />
            </tr>
          </thead>
          <tbody>
            {pageFlows.map((flow) => (
              <FlowBreakdownRow
                key={flow.flow_id}
                flow={flow}
                onExpand={onFlowExpand}
                dateRange={dateRange}
                selected={selectedIds?.has(flow.flow_id) ?? false}
                onSelectChange={(checked) => {
                  if (!onSelectionChange || !selectedIds) return;
                  const next = new Set(selectedIds);
                  if (checked) next.add(flow.flow_id);
                  else next.delete(flow.flow_id);
                  onSelectionChange(next);
                }}
              />
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between px-2 py-1 text-sm text-muted-foreground">
          <span>
            Page {page + 1} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              data-testid="pagination-prev"
              onClick={handlePrev}
              disabled={page === 0}
              className="px-3 py-1 border rounded disabled:opacity-40 hover:bg-muted/50 transition-colors"
            >
              Previous
            </button>
            <button
              data-testid="pagination-next"
              onClick={handleNext}
              disabled={page >= totalPages - 1}
              className="px-3 py-1 border rounded disabled:opacity-40 hover:bg-muted/50 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
