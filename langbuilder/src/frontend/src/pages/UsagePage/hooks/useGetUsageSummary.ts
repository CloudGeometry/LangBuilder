import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { getUsageSummary } from "@/services/LangWatchService";
import type { UsageQueryParams, UsageResponse } from "@/types/usage";

export const useGetUsageSummary = (params: UsageQueryParams) => {
  return useQuery<UsageResponse>({
    queryKey: ["usage", "summary", params],
    queryFn: () => getUsageSummary(params),
    staleTime: 4 * 60 * 1000, // 4 min — slightly less than Redis 5-min TTL
    gcTime: 10 * 60 * 1000, // 10 min garbage collection
    retry: 2, // NFR-012: retry 2x before error state
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 5000),
    placeholderData: keepPreviousData, // Show stale data during refetch (NFR-013-03)
  });
};
