'use client';

import { PlayCircle, CheckCircle, XCircle, Clock, Activity, AlertCircle } from 'lucide-react';
import { StatisticIcon } from '@/components/admin/StatisticIcon';
import { PageHeader } from '@/components/ui';
import { getStatusColor } from '@/lib/admin-utils';
import { AdminCard, AdminStatistic, AdminTable, AdminTag } from '@/components/admin/ui';
import type { AdminColumn } from '@/components/admin/ui';

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
  readonly items: Array<PipelineRun>;
  readonly total: number;
  readonly page: number;
  readonly page_size: number;
  readonly total_pages: number;
}

interface PipelineRunsClientProps {
  readonly pipelineStats: PipelineStats;
  readonly latestRun: PipelineRun | null;
  readonly pipelineRuns: PipelineRunsListResponse | null;
  readonly statusFilter: string;
  readonly currentPage: number;
}

function formatDate(dateString: string | null): string {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleString('en-US', {
    timeZone: 'UTC',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatStep(step: string | null): string {
  if (!step) return '-';
  return step.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function LatestRunStatus({ status }: { readonly status: string }) {
  if (status === 'running') {
    return (
      <AdminTag color="processing">
        <PlayCircle className="mr-1 inline h-3 w-3" />
        Currently Running
      </AdminTag>
    );
  }
  if (status === 'completed') {
    return (
      <AdminTag color="success">
        <CheckCircle className="mr-1 inline h-3 w-3" />
        Last Successful
      </AdminTag>
    );
  }
  return (
    <AdminTag color="error">
      <XCircle className="mr-1 inline h-3 w-3" />
      Last Failed
    </AdminTag>
  );
}

export default function PipelineRunsClient({
  pipelineStats,
  latestRun,
  pipelineRuns,
  statusFilter,
  currentPage,
}: PipelineRunsClientProps) {
  const columns: AdminColumn<PipelineRun>[] = [
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      priority: 'primary',
      render: (status: string) => (
        <AdminTag color={getStatusColor(status)}>{status.toUpperCase()}</AdminTag>
      ),
    },
    {
      title: 'Started At',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 180,
      priority: 'secondary',
      render: (date: string) => (
        <span className="text-foreground-secondary">{formatDate(date)}</span>
      ),
    },
    {
      title: 'Completed At',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 180,
      priority: 'detail',
      render: (date: string | null) => (
        <span className="text-foreground-secondary">{formatDate(date)}</span>
      ),
    },
    {
      title: 'Step Completed',
      dataIndex: 'step_completed',
      key: 'step_completed',
      ellipsis: true,
      priority: 'secondary',
      render: (step: string | null) => (
        <span className="text-foreground-secondary">{formatStep(step)}</span>
      ),
    },
    {
      title: 'Error',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
      priority: 'detail',
      render: (_error: string | null, record: PipelineRun) => {
        if (!record.error_message) return <span className="text-foreground-muted">-</span>;
        return (
          <div className="max-w-xs">
            <span className="dark:text-danger text-sm text-red-600">
              {record.error_step && <strong>[{formatStep(record.error_step)}]</strong>}{' '}
              {record.error_message}
            </span>
          </div>
        );
      },
    },
  ];

  const statusOptions = [
    { label: 'All', value: '' },
    { label: 'Running', value: 'running' },
    { label: 'Completed', value: 'completed' },
    { label: 'Failed', value: 'failed' },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pipeline Runs"
        description="Monitor job ingestion pipeline execution history"
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <StatisticIcon icon={Activity} />
            <AdminStatistic title="Total Runs" value={pipelineStats.total_runs} />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <div className="dark:bg-success/15 flex h-12 w-12 items-center justify-center rounded-lg bg-green-50">
              <CheckCircle className="dark:text-success h-6 w-6 text-green-600" />
            </div>
            <AdminStatistic
              title="Completed"
              value={pipelineStats.completed}
              valueClassName="text-green-600 dark:text-success"
            />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <div className="dark:bg-danger/15 flex h-12 w-12 items-center justify-center rounded-lg bg-red-50">
              <XCircle className="dark:text-danger h-6 w-6 text-red-600" />
            </div>
            <AdminStatistic
              title="Failed"
              value={pipelineStats.failed}
              valueClassName="text-red-600 dark:text-danger"
            />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <div className="bg-accent/15 flex h-12 w-12 items-center justify-center rounded-lg">
              <PlayCircle className="text-accent h-6 w-6" />
            </div>
            <AdminStatistic
              title="Currently Running"
              value={pipelineStats.running}
              valueClassName="text-accent"
            />
          </div>
        </AdminCard>
      </div>

      <AdminCard
        title={
          <span className="text-foreground flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Latest Run Status
          </span>
        }
      >
        {latestRun ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <span className="text-foreground-muted text-sm">Status</span>
              <div>
                <LatestRunStatus status={latestRun.status} />
              </div>
            </div>
            <div className="space-y-2">
              <span className="text-foreground-muted text-sm">
                {latestRun.status === 'running' ? 'Started At' : 'Completed At'}
              </span>
              <div className="text-foreground font-medium">
                {latestRun.status === 'running'
                  ? formatDate(latestRun.started_at)
                  : formatDate(latestRun.completed_at)}
              </div>
            </div>
            <div className="space-y-2">
              <span className="text-foreground-muted text-sm">
                {latestRun.status === 'running' ? 'Current Step' : 'Step Completed'}
              </span>
              <div className="text-foreground font-medium">
                {formatStep(latestRun.step_completed)}
              </div>
            </div>
            {latestRun.status === 'failed' && latestRun.error_message && (
              <div className="col-span-1 md:col-span-3">
                <div className="dark:border-danger/40 dark:bg-surface-inset rounded-lg border border-red-200 bg-red-50 p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="dark:text-danger mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
                    <div>
                      <p className="dark:text-danger text-sm font-medium text-red-800">
                        Error {latestRun.error_step && `in ${formatStep(latestRun.error_step)}`}
                      </p>
                      <p className="dark:text-danger mt-1 text-sm text-red-600">
                        {latestRun.error_message}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-foreground-muted py-8 text-center">
            No pipeline runs recorded yet
          </div>
        )}
      </AdminCard>

      <AdminCard
        title={
          <span className="text-foreground flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Pipeline Run History
          </span>
        }
        extra={
          <div className="flex flex-wrap gap-2">
            {statusOptions.map((option) => (
              <a
                key={option.value}
                href={`/admin/pipeline?status=${option.value}`}
                className={`rounded-md px-3 py-1 text-sm transition-colors ${
                  statusFilter === option.value
                    ? 'bg-accent text-on-accent'
                    : 'bg-surface-subtle text-foreground-secondary hover:bg-border'
                }`}
              >
                {option.label}
              </a>
            ))}
          </div>
        }
      >
        <AdminTable
          dataSource={pipelineRuns?.items || []}
          columns={columns}
          rowKey="id"
          pagination={
            pipelineRuns && pipelineRuns.total_pages > 1
              ? {
                  current: currentPage,
                  pageSize: 20,
                  total: pipelineRuns.total,
                  buildPageUrl: (page) => `/admin/pipeline?page=${page}&status=${statusFilter}`,
                }
              : false
          }
          size="middle"
          emptyText="No pipeline runs found"
        />
      </AdminCard>
    </div>
  );
}
