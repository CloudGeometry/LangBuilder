import { useState } from "react";
import type { FlowUsage } from "@/types/usage";
import { FlowRunsTable } from "./FlowRunsTable";

interface DateRange {
  from: string | null;
  to: string | null;
}

interface FlowBreakdownRowProps {
  flow: FlowUsage;
  onExpand: (flowId: string) => void;
  dateRange?: DateRange;
  selected?: boolean;
  onSelectChange?: (checked: boolean) => void;
}

export function FlowBreakdownRow({
  flow,
  onExpand,
  dateRange = { from: null, to: null },
  selected,
  onSelectChange,
}: FlowBreakdownRowProps) {
  const [expanded, setExpanded] = useState(false);

  const handleExpand = () => {
    setExpanded((prev) => !prev);
    onExpand(flow.flow_id);
  };

  const formatCost = (value: number) => `$${value.toFixed(4)}`;

  return (
    <>
      <tr
        data-testid={`flow-breakdown-row-${flow.flow_id}`}
        className="border-b hover:bg-muted/50 transition-colors"
      >
        <td className="px-4 py-3 w-10">
          <input
            type="checkbox"
            data-testid={`select-flow-${flow.flow_id}`}
            checked={selected ?? false}
            onChange={(e) => onSelectChange?.(e.target.checked)}
            className="h-4 w-4 rounded border-border"
          />
        </td>
        <td className="px-4 py-3 text-sm font-medium">{flow.flow_name}</td>
        <td className="px-4 py-3 text-sm text-muted-foreground">{flow.owner_username || "—"}</td>
        <td className="px-4 py-3 text-sm">{formatCost(flow.total_cost_usd)}</td>
        <td className="px-4 py-3 text-sm">{flow.invocation_count.toLocaleString()}</td>
        <td className="px-4 py-3 text-sm">{formatCost(flow.avg_cost_per_invocation_usd)}</td>
        <td className="px-4 py-3 text-sm">
          <button
            data-testid={`expand-btn-${flow.flow_id}`}
            onClick={handleExpand}
            className="text-xs text-muted-foreground hover:text-foreground border rounded px-2 py-1"
            aria-label={expanded ? "Collapse runs" : "Expand runs"}
          >
            {expanded ? "▲ Hide" : "▼ Runs"}
          </button>
        </td>
      </tr>
      {expanded && (
        <tr data-testid={`flow-runs-expanded-${flow.flow_id}`}>
          <td colSpan={7} className="px-0 py-0">
            <table className="w-full">
              <tbody>
                <FlowRunsTable flowId={flow.flow_id} dateRange={dateRange} />
              </tbody>
            </table>
          </td>
        </tr>
      )}
    </>
  );
}
