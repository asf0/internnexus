'use client';

import { PlayCircle, CheckCircle, XCircle, Clock, Activity, AlertCircle } from 'lucide-react';
import { StatisticIcon } from '@/components/admin/StatisticIcon';
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
  return step.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
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
      render: (status: string) => (
        <AdminTag color={getStatusColor(status)}>{status.toUpperCase()}</AdminTag>
      ),
    },
    {
      title: 'Started At',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 180,
      render: (date: string) => (
        <span className="text-slate-700 dark:text-slate-300">{formatDate(date)}</span>
      ),
    },
    {
      title: 'Completed At',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 180,
      render: (date: string | null) => (
        <span className="text-slate-700 dark:text-slate-300">{formatDate(date)}</span>
      ),
    },
    {
      title: 'Step Completed',
      dataIndex: 'step_completed',
      key: 'step_completed',
      ellipsis: true,
      render: (step: string | null) => (
        <span className="text-slate-700 dark:text-slate-300">{formatStep(step)}</span>
      ),
    },
    {
      title: 'Error',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
      render: (_error: string | null, record: PipelineRun) => {
        if (!record.error_message) return <span className="text-slate-400">-</span>;
        return (
          <div className="max-w-xs">
            <span className="text-sm text-red-600 dark:text-red-400">
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
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Pipeline Runs</h1>
        <p className="text-slate-600 dark:text-slate-400">
          Monitor job ingestion pipeline execution history
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <StatisticIcon icon={Activity} />
            <AdminStatistic
              title={<span className="text-slate-600 dark:text-slate-400">Total Runs</span>}
              value={pipelineStats.total_runs}
            />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-green-50 dark:bg-green-900/30">
              <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <AdminStatistic
              title={<span className="text-slate-600 dark:text-slate-400">Completed</span>}
              value={pipelineStats.completed}
              valueClassName="text-green-600 dark:text-green-400"
            />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-red-50 dark:bg-red-900/30">
              <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <AdminStatistic
              title={<span className="text-slate-600 dark:text-slate-400">Failed</span>}
              value={pipelineStats.failed}
              valueClassName="text-red-600 dark:text-red-400"
            />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-900/30">
              <PlayCircle className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <AdminStatistic
              title={<span className="text-slate-600 dark:text-slate-400">Currently Running</span>}
              value={pipelineStats.running}
              valueClassName="text-blue-600 dark:text-blue-400"
            />
          </div>
        </AdminCard>
      </div>

      <AdminCard
        title={
          <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
            <Clock className="h-5 w-5" />
            Latest Run Status
          </span>
        }
      >
        {latestRun ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <span className="text-sm text-slate-500 dark:text-slate-400">Status</span>
              <div>
                {latestRun.status === 'running' ? (
                  <AdminTag color="processing">
                    <PlayCircle className="mr-1 inline h-3 w-3" />
                    Currently Running
                  </AdminTag>
                ) : latestRun.status === 'completed' ? (
                  <AdminTag color="success">
                    <CheckCircle className="mr-1 inline h-3 w-3" />
                    Last Successful
                  </AdminTag>
                ) : (
                  <AdminTag color="error">
                    <XCircle className="mr-1 inline h-3 w-3" />
                    Last Failed
                  </AdminTag>
                )}
              </div>
            </div>
            <div className="space-y-2">
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {latestRun.status === 'running' ? 'Started At' : 'Completed At'}
              </span>
              <div className="font-medium text-slate-900 dark:text-slate-100">
                {latestRun.status === 'running'
                  ? formatDate(latestRun.started_at)
                  : formatDate(latestRun.completed_at)}
              </div>
            </div>
            <div className="space-y-2">
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {latestRun.status === 'running' ? 'Current Step' : 'Step Completed'}
              </span>
              <div className="font-medium text-slate-900 dark:text-slate-100">
                {formatStep(latestRun.step_completed)}
              </div>
            </div>
            {latestRun.status === 'failed' && latestRun.error_message && (
              <div className="col-span-1 md:col-span-3">
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600 dark:text-red-400" />
                    <div>
                      <p className="text-sm font-medium text-red-800 dark:text-red-200">
                        Error {latestRun.error_step && `in ${formatStep(latestRun.error_step)}`}
                      </p>
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                        {latestRun.error_message}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="py-8 text-center text-slate-500 dark:text-slate-400">
            No pipeline runs recorded yet
          </div>
        )}
      </AdminCard>

      <AdminCard
        title={
          <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
            <Activity className="h-5 w-5" />
            Pipeline Run History
          </span>
        }
        extra={
          <div className="flex gap-2">
            {statusOptions.map((option) => (
              <a
                key={option.value}
                href={`/admin/pipeline?status=${option.value}`}
                className={`rounded-md px-3 py-1 text-sm transition-colors ${
                  statusFilter === option.value
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600'
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
