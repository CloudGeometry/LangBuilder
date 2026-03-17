import type { FlowUsage } from "@/types/usage";

interface SelectionSummaryProps {
  selectedFlows: FlowUsage[];
}

export function SelectionSummary({ selectedFlows }: SelectionSummaryProps) {
  const count = selectedFlows.length;
  const totalCost = selectedFlows.reduce((sum, f) => sum + f.total_cost_usd, 0);
  const totalInvocations = selectedFlows.reduce((sum, f) => sum + f.invocation_count, 0);
  const avgCost = totalInvocations > 0 ? totalCost / totalInvocations : 0;

  const flowWord = count === 1 ? "flow" : "flows";

  return (
    <div
      data-testid="selection-summary"
      className="rounded-md border bg-muted/50 p-3 text-sm font-medium"
    >
      {count} {flowWord} selected: ${totalCost.toFixed(2)} total, {totalInvocations.toLocaleString()} invocations, ${avgCost.toFixed(2)} avg
    </div>
  );
}
