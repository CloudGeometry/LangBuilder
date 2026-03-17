import { useQuery } from "@tanstack/react-query";
import { getFlowRuns } from "@/services/LangWatchService";
import type { FlowRunsQueryParams, FlowRunsResponse } from "@/types/usage";

export const useGetFlowRuns = (
  flowId: string | null,
  params: FlowRunsQueryParams,
) => {
  return useQuery<FlowRunsResponse>({
    queryKey: ["usage", "flow-runs", flowId, params],
    queryFn: () => getFlowRuns(flowId!, params),
    enabled: flowId !== null, // Only fetch when a flow is expanded
    staleTime: 4 * 60 * 1000,
    retry: 2,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 5000),
  });
};
