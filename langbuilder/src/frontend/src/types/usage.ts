export interface UsageQueryParams {
  from_date?: string | null;
  to_date?: string | null;
  user_id?: string | null;
  sub_view?: "flows" | "mcp";
}

export interface FlowRunsQueryParams {
  from_date?: string | null;
  to_date?: string | null;
  limit?: number;
}

export interface UsageSummary {
  total_cost_usd: number;
  total_invocations: number;
  avg_cost_per_invocation_usd: number;
  active_flow_count: number;
  date_range: { from: string | null; to: string | null };
  currency: string;
  data_source: string;
  cached: boolean;
  cache_age_seconds: number | null;
  truncated: boolean;
}

export interface FlowUsage {
  flow_id: string;
  flow_name: string;
  total_cost_usd: number;
  invocation_count: number;
  avg_cost_per_invocation_usd: number;
  owner_user_id: string;
  owner_username: string;
}

export interface UsageResponse {
  summary: UsageSummary;
  flows: FlowUsage[];
}

export interface RunDetail {
  run_id: string;
  started_at: string;
  cost_usd: number;
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  model?: string;
  duration_ms?: number;
  status: "success" | "error" | "partial";
}

export interface FlowRunsResponse {
  flow_id: string;
  flow_name: string;
  runs: RunDetail[];
  total_runs_in_period: number;
}

export interface KeyStatusResponse {
  has_key: boolean;
  key_preview: string | null;
  configured_at: string | null;
}
