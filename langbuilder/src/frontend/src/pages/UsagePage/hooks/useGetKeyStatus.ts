import { useQuery } from "@tanstack/react-query";
import { getKeyStatus } from "@/services/LangWatchService";
import type { KeyStatusResponse } from "@/types/usage";

export const useGetKeyStatus = () => {
  return useQuery<KeyStatusResponse>({
    queryKey: ["usage", "key-status"],
    queryFn: getKeyStatus,
    staleTime: 5 * 60 * 1000, // 5 min — key status rarely changes
    retry: 1,
  });
};
