import { getBackendToken } from '@/lib/auth.server';
import {
  ClickStatsSchema,
  JobStatsSchema,
  PipelineRunSchema,
  PipelineStatsSchema,
} from '@/lib/schemas';
import { fetchAdminData } from '@/lib/admin-api';
import AdminDashboardClient from './AdminDashboardClient';

interface JobStats {
  total_jobs: number;
  active_jobs: number;
  total_companies: number;
  jobs_by_category: Record<string, number>;
}

interface ClickStats {
  total_clicks: number;
  clicks_today: number;
  clicks_this_week: number;
  clicks_this_month: number;
  top_jobs: Array<{
    job_id: string;
    title: string;
    company: string;
    click_count: number;
  }>;
}

interface PipelineStats {
  total_runs: number;
  completed: number;
  failed: number;
  running: number;
  last_success: string | null;
  last_failure: string | null;
}

interface PipelineRun {
  id: string;
  status: string;
  step_completed: string | null;
  error_message: string | null;
  error_step: string | null;
  started_at: string;
  completed_at: string | null;
  results: string | null;
}

export default async function AdminDashboardPage() {
  const token = await getBackendToken();
  if (!token) {
    return (
      <div className="rounded border border-slate-200 p-4 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
        Admin token unavailable. Please sign in again.
      </div>
    );
  }

  const [jobStats, clickStats, pipelineStats, latestRun] = await Promise.all([
    fetchAdminData<JobStats>('/admin/jobs/stats', JobStatsSchema),
    fetchAdminData<ClickStats>('/admin/clicks/stats', ClickStatsSchema),
    fetchAdminData<PipelineStats>('/admin/pipeline-runs/stats', PipelineStatsSchema),
    fetchAdminData<PipelineRun | null>('/admin/pipeline-runs/latest', PipelineRunSchema.nullable()),
  ]);

  if (!jobStats || !clickStats || !pipelineStats) {
    return (
      <div className="rounded border border-slate-200 p-4 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
        Failed to load admin dashboard data.
      </div>
    );
  }

  return (
    <AdminDashboardClient
      jobStats={jobStats}
      clickStats={clickStats}
      pipelineStats={pipelineStats}
      latestRun={latestRun}
    />
  );
}
