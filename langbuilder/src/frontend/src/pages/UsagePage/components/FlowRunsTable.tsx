import { useGetFlowRuns } from "../hooks/useGetFlowRuns";

interface DateRange {
  from: string | null;
  to: string | null;
}

interface FlowRunsTableProps {
  flowId: string;
  dateRange: DateRange;
}

export function FlowRunsTable({ flowId, dateRange }: FlowRunsTableProps) {
  const { data, isLoading, isError } = useGetFlowRuns(flowId, {
    from_date: dateRange.from,
    to_date: dateRange.to,
  });

  if (isLoading) {
    return (
      <tr data-testid="flow-runs-loading">
        <td colSpan={6} className="py-4 text-center text-sm text-muted-foreground">
          Loading runs...
        </td>
      </tr>
    );
  }

  if (isError) {
    return (
      <tr data-testid="flow-runs-error">
        <td colSpan={6} className="py-4 text-center text-sm text-destructive">
          Failed to load run data.
        </td>
      </tr>
    );
  }

  if (!data || data.runs.length === 0) {
    return (
      <tr data-testid="flow-runs-empty">
        <td colSpan={6} className="py-4 text-center text-sm text-muted-foreground">
          No runs found for this period.
        </td>
      </tr>
    );
  }

  return (
    <>
      <tr className="bg-muted/30">
        <th className="px-4 py-2 text-xs font-medium text-left text-muted-foreground">Run ID</th>
        <th className="px-4 py-2 text-xs font-medium text-left text-muted-foreground">Started At</th>
        <th className="px-4 py-2 text-xs font-medium text-left text-muted-foreground">Cost</th>
        <th className="px-4 py-2 text-xs font-medium text-left text-muted-foreground">Tokens</th>
        <th className="px-4 py-2 text-xs font-medium text-left text-muted-foreground">Model</th>
        <th className="px-4 py-2 text-xs font-medium text-left text-muted-foreground">Status</th>
      </tr>
      {data.runs.map((run) => {
        const truncatedId = run.run_id.length > 16
          ? `${run.run_id.slice(0, 8)}...${run.run_id.slice(-6)}`
          : run.run_id;
        const formattedDate = new Date(run.started_at).toLocaleString();
        const statusClass =
          run.status === "success"
            ? "text-green-600"
            : run.status === "error"
            ? "text-destructive"
            : "text-yellow-600";

        return (
          <tr key={run.run_id} data-testid={`run-row-${run.run_id}`} className="border-t">
            <td className="px-4 py-2 text-xs font-mono" title={run.run_id}>
              {truncatedId}
            </td>
            <td className="px-4 py-2 text-xs">{formattedDate}</td>
            <td className="px-4 py-2 text-xs">${run.cost_usd.toFixed(4)}</td>
            <td className="px-4 py-2 text-xs">{run.total_tokens?.toLocaleString() ?? "-"}</td>
            <td className="px-4 py-2 text-xs">{run.model ?? "-"}</td>
            <td className={`px-4 py-2 text-xs font-medium ${statusClass}`}>
              {run.status}
            </td>
          </tr>
        );
      })}
    </>
  );
}
