import { getBackendToken } from '@/lib/auth.server';
import {
  PipelineRunSchema,
  PipelineRunsListResponseSchema,
  PipelineStatsSchema,
} from '@/lib/schemas';
import { fetchAdminData } from '@/lib/admin-api';
import PipelineRunsClient from './PipelineRunsClient';

// Types for API responses
interface PipelineStats {
  readonly total_runs: number;
  readonly completed: number;
  readonly failed: number;
  readonly running: number;
  readonly last_success: string | null;
  readonly last_failure: string | null;
}

interface PipelineRun {
  readonly id: string;
  readonly status: string;
  readonly step_completed: string | null;
  readonly error_message: string | null;
  readonly error_step: string | null;
  readonly started_at: string;
  readonly completed_at: string | null;
  readonly results: string | null;
}

interface PipelineRunsListResponse {
  readonly items: PipelineRun[];
  readonly total: number;
  readonly page: number;
  readonly page_size: number;
  readonly total_pages: number;
}

export default async function PipelineRunsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; page?: string }>;
}) {
  const token = await getBackendToken();
  if (!token) {
    return (
      <div className="rounded border border-slate-200 p-4 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
        Admin token unavailable. Please sign in again.
      </div>
    );
  }

  // Get query params
  const params = await searchParams;
  const statusFilter = params.status || '';
  const currentPage = parseInt(params.page || '1', 10);

  // Fetch all data in parallel
  const [pipelineStats, latestRun, pipelineRuns] = await Promise.all([
    fetchAdminData<PipelineStats>('/admin/pipeline-runs/stats', PipelineStatsSchema),
    fetchAdminData<PipelineRun | null>('/admin/pipeline-runs/latest', PipelineRunSchema.nullable()),
    fetchAdminData<PipelineRunsListResponse>(
      `/admin/pipeline-runs?page=${currentPage}&page_size=20&status=${statusFilter}`,
      PipelineRunsListResponseSchema
    ),
  ]);

  if (!pipelineStats) {
    return (
      <div className="rounded border border-slate-200 p-4 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
        Failed to load pipeline admin data.
      </div>
    );
  }

  return (
    <PipelineRunsClient
      pipelineStats={pipelineStats}
      latestRun={latestRun}
      pipelineRuns={pipelineRuns}
      statusFilter={statusFilter}
      currentPage={currentPage}
    />
  );
}
