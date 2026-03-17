import type { UsageSummary } from "@/types/usage";

interface UsageSummaryCardsProps {
  summary: UsageSummary;
}

export function UsageSummaryCards({ summary }: UsageSummaryCardsProps) {
  return (
    <div className="grid grid-cols-4 gap-4" data-testid="usage-summary-cards">
      <div
        className="rounded-lg border p-4 space-y-1"
        data-testid="summary-card-total-cost"
      >
        <p className="text-sm text-muted-foreground">Total Cost</p>
        <p className="text-2xl font-bold">
          ${summary.total_cost_usd.toFixed(4)}
        </p>
      </div>
      <div
        className="rounded-lg border p-4 space-y-1"
        data-testid="summary-card-total-invocations"
      >
        <p className="text-sm text-muted-foreground">Total Invocations</p>
        <p className="text-2xl font-bold">
          {summary.total_invocations.toLocaleString()}
        </p>
      </div>
      <div
        className="rounded-lg border p-4 space-y-1"
        data-testid="summary-card-avg-cost"
      >
        <p className="text-sm text-muted-foreground">Avg Cost / Invocation</p>
        <p className="text-2xl font-bold">
          ${summary.avg_cost_per_invocation_usd.toFixed(4)}
        </p>
      </div>
      <div
        className="rounded-lg border p-4 space-y-1"
        data-testid="summary-card-active-flows"
      >
        <p className="text-sm text-muted-foreground">Active Flows</p>
        <p className="text-2xl font-bold">{summary.active_flow_count}</p>
      </div>
    </div>
  );
}
