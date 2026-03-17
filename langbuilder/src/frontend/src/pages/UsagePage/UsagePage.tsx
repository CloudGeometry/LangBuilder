import { useState } from "react";
import type { To } from "react-router-dom";
import { useGetUsageSummary } from "./hooks/useGetUsageSummary";
import { UsageLoadingSkeleton } from "./components/LoadingSkeleton";
import { UsageSummaryCards } from "./components/UsageSummaryCards";
import { DateRangePicker } from "./components/DateRangePicker";
import { UserFilterDropdown } from "./components/UserFilterDropdown";
import { useDebounce } from "@/hooks/useDebounce";
import PageLayout from "@/components/common/pageLayout";

interface DateRange {
  from: string | null;
  to: string | null;
}

export function UsagePage() {
  const [dateRange, setDateRange] = useState<DateRange>({ from: null, to: null });
  const [userId, setUserId] = useState<string | null>(null);

  const debouncedDateRange = useDebounce(dateRange, 500);

  const { data, isLoading, isError, error } = useGetUsageSummary({
    from_date: debouncedDateRange.from,
    to_date: debouncedDateRange.to,
    user_id: userId,
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
          <div
            className="flex h-full flex-1 flex-col items-center justify-center text-center"
            data-testid="usage-no-key-state"
          >
            <h2 className="text-lg font-semibold">No API Key Configured</h2>
            <p className="text-sm text-muted-foreground mt-2">
              Configure your LangWatch API key in Settings to start tracking usage.
            </p>
          </div>
        </PageLayout>
      );
    }

    const retryable = (error as any)?.retryable;

    return (
      <PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>
        <div
          className="flex h-full flex-1 flex-col items-center justify-center text-center"
          data-testid="usage-error-state"
        >
          <h2 className="text-lg font-semibold text-destructive">
            Failed to load usage data
          </h2>
          <p className="text-sm text-muted-foreground mt-2">
            {error instanceof Error ? error.message : "An error occurred"}
          </p>
          {retryable && (
            <p className="text-xs text-muted-foreground mt-1">
              This may be temporary. Try refreshing.
            </p>
          )}
        </div>
      </PageLayout>
    );
  }

  if (!data) {
    return (
      <PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>
        <div
          className="flex h-full flex-1 flex-col items-center justify-center text-center"
          data-testid="usage-empty-state"
        >
          <h2 className="text-lg font-semibold">No usage data available</h2>
          <p className="text-sm text-muted-foreground mt-2">
            Configure your LangWatch API key to start tracking usage.
          </p>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>
      <div className="space-y-6 p-6" data-testid="usage-dashboard">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Usage</h1>
          <div className="flex gap-4 items-center">
            <DateRangePicker value={dateRange} onChange={setDateRange} />
            <UserFilterDropdown
              value={userId}
              onChange={setUserId}
              users={[]}
            />
          </div>
        </div>
        <UsageSummaryCards summary={data.summary} />
      </div>
    </PageLayout>
  );
}
