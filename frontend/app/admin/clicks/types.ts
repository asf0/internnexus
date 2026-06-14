export interface ClickStats {
  readonly total_clicks: number;
  readonly clicks_today: number;
  readonly clicks_this_week: number;
  readonly clicks_this_month: number;
  readonly authenticated_clicks_total: number;
  readonly anonymous_clicks_total: number;
  readonly unique_users_total: number;
  readonly unique_jobs_total: number;
  readonly clicks_last_24h: number;
  readonly avg_clicks_per_day_30d: number;
  readonly top_sources: Array<{ readonly value: string; readonly click_count: number }>;
  readonly top_mediums: Array<{ readonly value: string; readonly click_count: number }>;
  readonly top_campaigns: Array<{ readonly value: string; readonly click_count: number }>;
  readonly clicks_by_hour_today: Array<{ readonly hour: number; readonly clicks: number }>;
  readonly daily_breakdown_14d: Array<{
    readonly date: string;
    readonly clicks: number;
    readonly unique_users: number;
  }>;
  readonly top_jobs: Array<{
    readonly job_id: string;
    readonly title: string;
    readonly company: string;
    readonly click_count: number;
  }>;
}

export interface ClickByDay {
  readonly date: string;
  readonly clicks: number;
  readonly unique_users?: number;
  readonly unique_jobs?: number;
}

export interface JobClick {
  readonly id: string;
  readonly job_id: string;
  readonly job_title: string;
  readonly company: string;
  readonly apply_url: string | null;
  readonly user_id: string | null;
  readonly user_email: string | null;
  readonly user_name: string | null;
  readonly clicked_at: string;
  readonly utm_source: string;
  readonly utm_medium: string | null;
  readonly utm_campaign: string | null;
}

export interface ClicksByUser {
  readonly user_id: string | null;
  readonly email: string | null;
  readonly name: string | null;
  readonly click_count: number;
}

export interface ClicksListResponse {
  readonly items: JobClick[];
  readonly total: number;
  readonly page: number;
  readonly page_size: number;
  readonly total_pages: number;
}
