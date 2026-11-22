export interface McpUsageStats {
  readonly total_calls: number;
  readonly calls_today: number;
  readonly calls_this_week: number;
  readonly calls_this_month: number;
  readonly success_rate: number;
  readonly average_duration_ms: number;
  readonly unique_users: number;
  readonly unique_keys: number;
  readonly search_count: number;
  readonly average_search_result_count: number;
}

export interface McpToolUsage {
  readonly tool_name: string;
  readonly total_calls: number;
  readonly successful_calls: number;
  readonly failed_calls: number;
  readonly success_rate: number;
  readonly average_duration_ms: number;
  readonly average_result_count: number | null;
}

export interface McpDailyUsage {
  readonly date: string;
  readonly total_calls: number;
  readonly successful_calls: number;
  readonly failed_calls: number;
  readonly unique_users: number;
}

export interface McpUsageEvent {
  readonly id: string;
  readonly user_id: string | null;
  readonly mcp_key_id: string | null;
  readonly tool_name: string;
  readonly called_at: string;
  readonly success: boolean;
  readonly duration_ms: number;
  readonly job_id: string | null;
  readonly result_count: number | null;
  readonly error_category: string | null;
  readonly metadata: Record<string, unknown>;
}

export interface McpUsageEventsResponse {
  readonly items: McpUsageEvent[];
  readonly total: number;
  readonly page: number;
  readonly page_size: number;
  readonly total_pages: number;
}
