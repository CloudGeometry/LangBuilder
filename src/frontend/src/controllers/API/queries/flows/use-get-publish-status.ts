import type { UseQueryResult } from "@tanstack/react-query";
import type { useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export interface IPublishRecord {
  id: string;
  flow_id: string;
  platform: string;
  platform_url: string;
  external_id: string;
  published_at: string;
  published_by: string;
  status: "ACTIVE" | "UNPUBLISHED" | "ERROR" | "PENDING";
  metadata: {
    model_name?: string;
    pipe_function_deployed?: boolean;
  } | null;
  last_sync_at: string | null;
  error_message: string | null;
}

export interface IGetPublishStatusParams {
  flow_id: string;
}

export const useGetPublishStatus: useQueryFunctionType<
  IGetPublishStatusParams,
  IPublishRecord[]
> = (params, options?) => {
  const { query } = UseRequestProcessor();

  const getPublishStatusFn = async (): Promise<IPublishRecord[]> => {
    if (!params?.flow_id) {
      return [];
    }

    const response = await api.get<IPublishRecord[]>(
      `${getURL("PUBLISH")}/status/${params.flow_id}`,
    );
    return response.data;
  };

  const queryResult: UseQueryResult<IPublishRecord[]> = query(
    ["useGetPublishStatus", params?.flow_id],
    getPublishStatusFn,
    {
      enabled: !!params?.flow_id,
      ...options,
    },
  );

  return queryResult;
};
