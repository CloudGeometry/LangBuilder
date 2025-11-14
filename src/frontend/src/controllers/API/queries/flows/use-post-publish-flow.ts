import type { UseMutationResult } from "@tanstack/react-query";
import type { useMutationFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export interface IPublishFlowRequest {
  flow_id: string;
  openwebui_url: string;
  openwebui_api_key: string;
  model_name?: string;
}

export interface IPublishFlowResponse {
  success: boolean;
  model_id: string;
  model_name: string;
  openwebui_url: string;
  pipe_function_deployed: boolean;
  message: string;
}

export const usePostPublishFlow: useMutationFunctionType<
  IPublishFlowResponse,
  IPublishFlowRequest
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const publishFlowFn = async (
    payload: IPublishFlowRequest,
  ): Promise<IPublishFlowResponse> => {
    const response = await api.post<IPublishFlowResponse>(
      `${getURL("PUBLISH")}/openwebui`,
      {
        flow_id: payload.flow_id,
        openwebui_url: payload.openwebui_url,
        openwebui_api_key: payload.openwebui_api_key,
        ...(payload.model_name && { model_name: payload.model_name }),
      },
    );
    return response.data;
  };

  const mutation: UseMutationResult<
    IPublishFlowResponse,
    any,
    IPublishFlowRequest
  > = mutate(["usePostPublishFlow"], publishFlowFn, {
    ...options,
    onSettled: (response) => {
      if (response?.flow_id) {
        // Refetch publish status for this flow
        queryClient.invalidateQueries({
          queryKey: ["useGetPublishStatus", response.flow_id],
        });
      }
    },
  });

  return mutation;
};
