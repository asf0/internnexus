import { getBackendToken } from "@/lib/auth.server";
import { BACKEND_URL } from "@/lib/config";
import PipelineRunsClient from "./PipelineRunsClient";

// Types for API responses
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

interface PipelineRunsListResponse {
  items: PipelineRun[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Fetch helper with auth
async function fetchAdminEndpoint<T>(
  endpoint: string,
  token: string
): Promise<T | null> {
  try {
    const response = await fetch(`${BACKEND_URL}${endpoint}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as T;
  } catch {
    return null;
  }
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
  const statusFilter = params.status || "";
  const currentPage = parseInt(params.page || "1", 10);

  // Fetch all data in parallel
  const [pipelineStats, latestRun, pipelineRuns] = await Promise.all([
    fetchAdminEndpoint<PipelineStats>("/admin/pipeline-runs/stats", token),
    fetchAdminEndpoint<PipelineRun | null>("/admin/pipeline-runs/latest", token),
    fetchAdminEndpoint<PipelineRunsListResponse>(
      `/admin/pipeline-runs?page=${currentPage}&page_size=20&status=${statusFilter}`,
      token
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
