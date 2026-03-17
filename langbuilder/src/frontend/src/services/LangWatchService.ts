import { BASE_URL_API } from "@/constants/constants";
import type {
  FlowRunsQueryParams,
  FlowRunsResponse,
  KeyStatusResponse,
  UsageQueryParams,
  UsageResponse,
} from "@/types/usage";

// Use the same base URL pattern as the rest of the app
const BASE_URL_API_V1 = BASE_URL_API;

export const getUsageSummary = async (
  params: UsageQueryParams,
): Promise<UsageResponse> => {
  const searchParams = new URLSearchParams();
  if (params.from_date) searchParams.set("from_date", params.from_date);
  if (params.to_date) searchParams.set("to_date", params.to_date);
  if (params.user_id) searchParams.set("user_id", params.user_id);
  if (params.sub_view) searchParams.set("sub_view", params.sub_view);

  const response = await fetch(`${BASE_URL_API_V1}usage/?${searchParams}`, {
    credentials: "include",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = data?.detail;
    const message =
      (typeof detail === "object" ? detail?.message : detail) ||
      data?.message ||
      response.statusText ||
      "Unknown error";
    const err = new Error(message);
    (err as any).code = typeof detail === "object" ? detail?.code : undefined;
    (err as any).retryable = typeof detail === "object" ? detail?.retryable : undefined;
    throw err;
  }
  return response.json();
};

export const getFlowRuns = async (
  flowId: string,
  params: FlowRunsQueryParams,
): Promise<FlowRunsResponse> => {
  const searchParams = new URLSearchParams();
  if (params.from_date) searchParams.set("from_date", params.from_date);
  if (params.to_date) searchParams.set("to_date", params.to_date);
  if (params.limit) searchParams.set("limit", String(params.limit));

  const response = await fetch(
    `${BASE_URL_API_V1}usage/${flowId}/runs?${searchParams}`,
    {
      credentials: "include",
    },
  );
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = data?.detail;
    const message =
      (typeof detail === "object" ? detail?.message : detail) ||
      data?.message ||
      response.statusText ||
      "Unknown error";
    const err = new Error(message);
    (err as any).code = typeof detail === "object" ? detail?.code : undefined;
    (err as any).retryable = typeof detail === "object" ? detail?.retryable : undefined;
    throw err;
  }
  return response.json();
};

export const getKeyStatus = async (): Promise<KeyStatusResponse> => {
  const response = await fetch(
    `${BASE_URL_API_V1}usage/settings/langwatch-key/status`,
    {
      credentials: "include",
    },
  );
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = data?.detail;
    const message =
      (typeof detail === "object" ? detail?.message : detail) ||
      data?.message ||
      response.statusText ||
      "Unknown error";
    const err = new Error(message);
    (err as any).code = typeof detail === "object" ? detail?.code : undefined;
    (err as any).retryable = typeof detail === "object" ? detail?.retryable : undefined;
    throw err;
  }
  return response.json();
};

export const saveLangWatchKey = async (
  apiKey: string,
): Promise<{ success: boolean; key_preview: string; message: string }> => {
  const response = await fetch(
    `${BASE_URL_API_V1}usage/settings/langwatch-key`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({ api_key: apiKey }),
    },
  );
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = data?.detail;
    const message =
      (typeof detail === "object" ? detail?.message : detail) ||
      data?.message ||
      response.statusText ||
      "Unknown error";
    const err = new Error(message);
    (err as any).code = typeof detail === "object" ? detail?.code : undefined;
    (err as any).retryable = typeof detail === "object" ? detail?.retryable : undefined;
    throw err;
  }
  return response.json();
};
