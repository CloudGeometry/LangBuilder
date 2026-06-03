import { useEffect, useState } from "react";
import type { To } from "react-router-dom";
import { useGetUsageSummary } from "./hooks/useGetUsageSummary";
import { UsageLoadingSkeleton } from "./components/LoadingSkeleton";
import { UsageSummaryCards } from "./components/UsageSummaryCards";
import { FlowBreakdownList } from "./components/FlowBreakdownList";
import { EmptyStatePrompt } from "./components/EmptyStatePrompt";
import { ErrorState } from "./components/ErrorState";
import { DateRangePicker } from "./components/DateRangePicker";
import { UserFilterDropdown } from "./components/UserFilterDropdown";
import { SubViewToggle } from "./components/SubViewToggle";
import { SelectionSummary } from "./components/SelectionSummary";
import { useDebounce } from "@/hooks/useDebounce";
import useAuthStore from "@/stores/authStore";
import PageLayout from "@/components/common/pageLayout";

interface DateRange {
  from: string | null;
  to: string | null;
}

export function UsagePage() {
  const [dateRange, setDateRange] = useState<DateRange>({ from: null, to: null });
  const [userId, setUserId] = useState<string | null>(null);
  const [, setExpandedFlowId] = useState<string | null>(null);
  const [subView, setSubView] = useState<"flows" | "mcp">("flows");
  const [selectedFlowIds, setSelectedFlowIds] = useState<Set<string>>(new Set());

  const isAdmin = useAuthStore((state) => state.isAdmin);

  const debouncedDateRange = useDebounce(dateRange, 500);

  useEffect(() => {
    setSelectedFlowIds(new Set());
  }, [debouncedDateRange, userId]);

  const { data, isLoading, isError, error, refetch } = useGetUsageSummary({
    from_date: debouncedDateRange.from,
    to_date: debouncedDateRange.to,
    user_id: userId,
    sub_view: subView,
  });

  if (isLoading && !data) {
    return (
      <PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>
        <UsageLoadingSkeleton />
      </PageLayout>
    );
  }

  if (isError) {
    const errCode = (error as any)?.code;

    if (errCode === "KEY_NOT_CONFIGURED") {
      return (
        <PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>
          <EmptyStatePrompt variant="no_key" isAdmin={isAdmin} />
        </PageLayout>
      );
    }

    return (
      <PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>
        <ErrorState error={error} onRetry={() => refetch()} />
      </PageLayout>
    );
  }

  if (!data) {
    return (
      <PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>
        <EmptyStatePrompt variant="no_data" isAdmin={isAdmin} />
      </PageLayout>
    );
  }

  const uniqueUsers = (() => {
    const seen = new Map<string, string>();
    for (const flow of data.flows) {
      if (flow.owner_user_id && !seen.has(flow.owner_user_id)) {
        seen.set(flow.owner_user_id, flow.owner_username);
      }
    }
    return Array.from(seen, ([id, username]) => ({ id, username }));
  })();

  const selectedFlows = data.flows.filter(f => selectedFlowIds.has(f.flow_id));

  return (
    <PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>
      <div className="space-y-6 p-6" data-testid="usage-dashboard">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Usage</h1>
          <div className="flex gap-4 items-center">
            <DateRangePicker value={dateRange} onChange={setDateRange} />
            {isAdmin && (
              <UserFilterDropdown
                value={userId}
                onChange={setUserId}
                users={uniqueUsers}
              />
            )}
          </div>
        </div>
        <SubViewToggle value={subView} onChange={setSubView} />
        <UsageSummaryCards summary={data.summary} />
        {selectedFlows.length > 0 && (
          <SelectionSummary selectedFlows={selectedFlows} />
        )}
        <FlowBreakdownList
          flows={data.flows}
          onFlowExpand={setExpandedFlowId}
          dateRange={dateRange}
          selectedIds={selectedFlowIds}
          onSelectionChange={setSelectedFlowIds}
        />
      </div>
    </PageLayout>
  );
}
