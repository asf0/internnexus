'use client';

import {
  Briefcase,
  Building2,
  MousePointer,
  Activity,
  CheckCircle,
  PlayCircle,
  Clock,
  TrendingUp,
} from 'lucide-react';
import { StatisticIcon } from '@/components/admin/StatisticIcon';
import { getStatusColor } from '@/lib/admin-utils';
import { AdminCard, AdminStatistic, AdminTable, AdminTag } from '@/components/admin/ui';
import type { AdminColumn } from '@/components/admin/ui';

interface JobStats {
  readonly total_jobs: number;
  readonly active_jobs: number;
  readonly total_companies: number;
  readonly jobs_by_category: Record<string, number>;
}

interface ClickStats {
  readonly total_clicks: number;
  readonly clicks_today: number;
  readonly clicks_this_week: number;
  readonly clicks_this_month: number;
  readonly top_jobs: ReadonlyArray<{
    readonly job_id: string;
    readonly title: string;
    readonly company: string;
    readonly click_count: number;
  }>;
}

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

interface AdminDashboardClientProps {
  readonly jobStats: JobStats;
  readonly clickStats: ClickStats;
  readonly pipelineStats: PipelineStats;
  readonly latestRun: PipelineRun | null;
}

function formatDate(dateString: string | null): string {
  if (!dateString) return 'Never';
  return new Date(dateString).toLocaleString('en-US', {
    timeZone: 'UTC',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function AdminDashboardClient({
  jobStats,
  clickStats,
  pipelineStats,
  latestRun,
}: AdminDashboardClientProps) {
  const topJobsColumns: AdminColumn<(typeof clickStats.top_jobs)[number]>[] = [
    { title: 'Job Title', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: 'Company', dataIndex: 'company', key: 'company', ellipsis: true },
    {
      title: 'Clicks',
      dataIndex: 'click_count',
      key: 'click_count',
      render: (count: number) => (
        <span className="text-accent font-semibold">{count.toLocaleString()}</span>
      ),
    },
  ];

  const categoryColumns: AdminColumn<{ category: string; count: number }>[] = [
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => <AdminTag color="blue">{category}</AdminTag>,
    },
    {
      title: 'Jobs',
      dataIndex: 'count',
      key: 'count',
      render: (count: number) => <span className="font-semibold">{count.toLocaleString()}</span>,
    },
  ];

  const categoryData = Object.entries(jobStats.jobs_by_category)
    .map(([category, count]) => ({ category, count }))
    .sort((a, b) => b.count - a.count);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-foreground text-2xl font-bold">Admin Dashboard</h1>
          <p className="text-foreground-muted">Overview of system statistics and activity</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <StatisticIcon icon={Briefcase} />
            <AdminStatistic title="Total Jobs" value={jobStats.total_jobs} />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <StatisticIcon icon={CheckCircle} />
            <AdminStatistic
              title="Active Jobs"
              value={jobStats.active_jobs}
              valueClassName="text-green-600 dark:text-success"
            />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <StatisticIcon icon={Building2} />
            <AdminStatistic title="Total Companies" value={jobStats.total_companies} />
          </div>
        </AdminCard>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <StatisticIcon icon={MousePointer} />
            <AdminStatistic title="Total Clicks" value={clickStats.total_clicks} />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <StatisticIcon icon={TrendingUp} />
            <AdminStatistic
              title="Clicks Today"
              value={clickStats.clicks_today}
              valueClassName="text-accent"
            />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <StatisticIcon icon={Activity} />
            <AdminStatistic title="Clicks This Week" value={clickStats.clicks_this_week} />
          </div>
        </AdminCard>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <AdminCard
          title={
            <span className="text-foreground flex items-center gap-2">
              <PlayCircle className="h-5 w-5" />
              Pipeline Status
            </span>
          }
        >
          <div className="grid grid-cols-3 gap-4">
            <AdminStatistic
              title="Total Runs"
              value={pipelineStats.total_runs}
              valueClassName="text-2xl"
            />
            <AdminStatistic
              title="Completed"
              value={pipelineStats.completed}
              valueClassName="text-2xl text-green-600 dark:text-success"
            />
            <AdminStatistic
              title="Failed"
              value={pipelineStats.failed}
              valueClassName="text-2xl text-red-600 dark:text-danger"
            />
          </div>
          {pipelineStats.running > 0 && (
            <div className="border-border mt-4 border-t pt-4">
              <AdminTag color="processing">
                <PlayCircle className="mr-1 inline h-3 w-3" />
                {pipelineStats.running} currently running
              </AdminTag>
            </div>
          )}
        </AdminCard>

        <AdminCard
          title={
            <span className="text-foreground flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Last Run Status
            </span>
          }
        >
          {latestRun ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-foreground-muted">Status:</span>
                <AdminTag color={getStatusColor(latestRun.status)}>
                  {latestRun.status.toUpperCase()}
                </AdminTag>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-foreground-muted">Started:</span>
                <span className="text-foreground">{formatDate(latestRun.started_at)}</span>
              </div>
              {latestRun.completed_at && (
                <div className="flex items-center justify-between">
                  <span className="text-foreground-muted">Completed:</span>
                  <span className="text-foreground">{formatDate(latestRun.completed_at)}</span>
                </div>
              )}
              {latestRun.error_message && (
                <div className="dark:bg-surface-inset mt-2 rounded-lg bg-red-50 p-3">
                  <p className="dark:text-danger text-sm text-red-600">
                    <strong>Error:</strong> {latestRun.error_message}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-foreground-muted py-4 text-center">
              No pipeline runs recorded yet
            </div>
          )}
        </AdminCard>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <AdminCard
          title={
            <span className="text-foreground flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Top Jobs by Clicks
            </span>
          }
        >
          <AdminTable
            dataSource={clickStats.top_jobs.slice(0, 5)}
            columns={topJobsColumns}
            rowKey="job_id"
            pagination={false}
            size="small"
            emptyText="No clicks recorded yet"
          />
        </AdminCard>

        <AdminCard
          title={
            <span className="text-foreground flex items-center gap-2">
              <Briefcase className="h-5 w-5" />
              Jobs by Category
            </span>
          }
        >
          <AdminTable
            dataSource={categoryData}
            columns={categoryColumns}
            rowKey="category"
            pagination={false}
            size="small"
            emptyText="No categories found"
          />
        </AdminCard>
      </div>
    </div>
  );
}
