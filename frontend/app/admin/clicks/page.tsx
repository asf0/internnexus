import { getBackendToken } from '@/lib/auth.server';
import { ClickByDayArraySchema, ClickStatsSchema, ClicksListResponseSchema } from '@/lib/schemas';
import { fetchAdminData } from '@/lib/admin-api';
import { ClicksClient } from './ClicksClient';

// Types for API responses
interface ClickStats {
  total_clicks: number;
  clicks_today: number;
  clicks_this_week: number;
  clicks_this_month: number;
  authenticated_clicks_total: number;
  anonymous_clicks_total: number;
  unique_users_total: number;
  unique_jobs_total: number;
  clicks_last_24h: number;
  avg_clicks_per_day_30d: number;
  top_sources: Array<{ value: string; click_count: number }>;
  top_mediums: Array<{ value: string; click_count: number }>;
  top_campaigns: Array<{ value: string; click_count: number }>;
  clicks_by_hour_today: Array<{ hour: number; clicks: number }>;
  daily_breakdown_14d: Array<{ date: string; clicks: number; unique_users: number }>;
  top_jobs: Array<{
    job_id: string;
    title: string;
    company: string;
    click_count: number;
  }>;
}

interface ClickByDay {
  date: string;
  clicks: number;
  unique_users?: number;
  unique_jobs?: number;
}

interface JobClick {
  id: string;
  job_id: string;
  job_title: string;
  company: string;
  user_id: string | null;
  user_email: string | null;
  user_name: string | null;
  clicked_at: string;
  utm_source: string;
  utm_medium: string | null;
  utm_campaign: string | null;
  apply_url: string | null;
}

interface ClicksListResponse {
  items: JobClick[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export default async function AdminClicksPage() {
  const token = await getBackendToken();
  if (!token) {
    return (
      <div className="rounded border border-slate-200 p-4 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
        Admin token unavailable. Please sign in again.
      </div>
    );
  }

  // Fetch all data in parallel
  const [clickStats, clicksByDay, recentClicks] = await Promise.all([
    fetchAdminData<ClickStats>('/admin/clicks/stats', ClickStatsSchema),
    fetchAdminData<ClickByDay[]>('/admin/clicks/by-day?days=30', ClickByDayArraySchema),
    fetchAdminData<ClicksListResponse>(
      '/admin/clicks?page=1&page_size=50',
      ClicksListResponseSchema
    ),
  ]);

  if (!clickStats) {
    return (
      <div className="rounded border border-slate-200 p-4 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
        Failed to load click analytics.
      </div>
    );
  }

  return (
    <ClicksClient clickStats={clickStats} clicksByDay={clicksByDay} recentClicks={recentClicks} />
  );
}
