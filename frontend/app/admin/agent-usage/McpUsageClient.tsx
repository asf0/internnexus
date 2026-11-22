'use client';

import { Activity, Bot, CheckCircle, Clock, KeyRound, Search, Users } from 'lucide-react';
import { StatisticIcon } from '@/components/admin/StatisticIcon';
import { PageHeader } from '@/components/ui';
import { AdminCard, AdminStatistic, AdminTable, AdminTag } from '@/components/admin/ui';
import type { AdminColumn } from '@/components/admin/ui';
import type {
  McpDailyUsage,
  McpToolUsage,
  McpUsageEvent,
  McpUsageEventsResponse,
  McpUsageStats,
} from './types';

interface McpUsageClientProps {
  readonly stats: McpUsageStats;
  readonly tools: McpToolUsage[] | null;
  readonly daily: McpDailyUsage[] | null;
  readonly events: McpUsageEventsResponse | null;
  readonly filters: {
    readonly tool: string;
    readonly status: string;
    readonly dateFrom: string;
    readonly dateTo: string;
    readonly page: number;
  };
}

const formatDuration = (value: number) =>
  `${value.toLocaleString('en-US', { maximumFractionDigits: 1 })} ms`;
const formatRate = (value: number) =>
  `${value.toLocaleString('en-US', { maximumFractionDigits: 1 })}%`;
const formatDateTime = (value: string) => new Date(value).toLocaleString();

export default function McpUsageClient({
  stats,
  tools,
  daily,
  events,
  filters,
}: McpUsageClientProps) {
  const toolColumns: AdminColumn<McpToolUsage>[] = [
    {
      title: 'Tool',
      dataIndex: 'tool_name',
      key: 'tool_name',
      priority: 'primary',
      mobileLabel: 'Tool',
      render: (value) => <code>{value}</code>,
    },
    {
      title: 'Calls',
      dataIndex: 'total_calls',
      key: 'total_calls',
      align: 'right',
      priority: 'secondary',
    },
    {
      title: 'Succeeded',
      dataIndex: 'successful_calls',
      key: 'successful_calls',
      align: 'right',
      priority: 'detail',
    },
    {
      title: 'Failed',
      dataIndex: 'failed_calls',
      key: 'failed_calls',
      align: 'right',
      priority: 'detail',
    },
    {
      title: 'Success rate',
      dataIndex: 'success_rate',
      key: 'success_rate',
      align: 'right',
      priority: 'secondary',
      render: formatRate,
    },
    {
      title: 'Avg duration',
      dataIndex: 'average_duration_ms',
      key: 'average_duration_ms',
      align: 'right',
      priority: 'detail',
      render: formatDuration,
    },
    {
      title: 'Avg results',
      dataIndex: 'average_result_count',
      key: 'average_result_count',
      align: 'right',
      priority: 'detail',
      render: (value: number | null) => (value == null ? '—' : value.toFixed(1)),
    },
  ];

  const dailyColumns: AdminColumn<McpDailyUsage>[] = [
    { title: 'Date', dataIndex: 'date', key: 'date', priority: 'primary' },
    {
      title: 'Calls',
      dataIndex: 'total_calls',
      key: 'total_calls',
      align: 'right',
      priority: 'secondary',
    },
    {
      title: 'Succeeded',
      dataIndex: 'successful_calls',
      key: 'successful_calls',
      align: 'right',
      priority: 'detail',
    },
    {
      title: 'Failed',
      dataIndex: 'failed_calls',
      key: 'failed_calls',
      align: 'right',
      priority: 'detail',
    },
    {
      title: 'Unique users',
      dataIndex: 'unique_users',
      key: 'unique_users',
      align: 'right',
      priority: 'secondary',
    },
  ];

  const eventColumns: AdminColumn<McpUsageEvent>[] = [
    {
      title: 'Time',
      dataIndex: 'called_at',
      key: 'called_at',
      width: 180,
      priority: 'secondary',
      render: (value: string) => formatDateTime(value),
    },
    {
      title: 'Tool',
      dataIndex: 'tool_name',
      key: 'tool_name',
      priority: 'primary',
      render: (value) => <code>{value}</code>,
    },
    {
      title: 'Status',
      dataIndex: 'success',
      key: 'success',
      priority: 'secondary',
      render: (success: boolean) => (
        <AdminTag color={success ? 'success' : 'error'}>{success ? 'SUCCESS' : 'FAILED'}</AdminTag>
      ),
    },
    {
      title: 'Duration',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      align: 'right',
      priority: 'detail',
      render: formatDuration,
    },
    {
      title: 'Results',
      dataIndex: 'result_count',
      key: 'result_count',
      align: 'right',
      priority: 'detail',
      render: (value) => value ?? '—',
    },
    {
      title: 'User',
      dataIndex: 'user_id',
      key: 'user_id',
      ellipsis: true,
      priority: 'detail',
      render: (value) => value || 'Deleted / unknown',
    },
    {
      title: 'Key',
      dataIndex: 'mcp_key_id',
      key: 'mcp_key_id',
      ellipsis: true,
      priority: 'detail',
      render: (value) => value || 'Deleted / unknown',
    },
    {
      title: 'Context',
      key: 'context',
      ellipsis: true,
      priority: 'detail',
      render: (_value, event) =>
        event.error_category ||
        (event.job_id ? `Job ${event.job_id}` : JSON.stringify(event.metadata || {})),
    },
  ];

  const buildEventsUrl = (page: number) => {
    const params = new URLSearchParams();
    if (filters.tool) params.set('tool', filters.tool);
    if (filters.status) params.set('status', filters.status);
    if (filters.dateFrom) params.set('date_from', filters.dateFrom);
    if (filters.dateTo) params.set('date_to', filters.dateTo);
    if (page > 1) params.set('page', String(page));
    const query = params.toString();
    const suffix = query ? `?${query}` : '';
    return `/admin/agent-usage${suffix}`;
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="MCP usage"
        description="Monitor AI-agent tool activity, reliability, and adoption."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { title: 'Total calls', value: stats.total_calls, icon: Activity },
          { title: 'Calls today', value: stats.calls_today, icon: Bot },
          { title: 'Success rate', value: formatRate(stats.success_rate), icon: CheckCircle },
          { title: 'Avg duration', value: formatDuration(stats.average_duration_ms), icon: Clock },
          { title: 'Unique users', value: stats.unique_users, icon: Users },
          { title: 'Unique keys', value: stats.unique_keys, icon: KeyRound },
          { title: 'Searches', value: stats.search_count, icon: Search },
          {
            title: 'Avg search results',
            value: stats.average_search_result_count.toFixed(1),
            icon: Search,
          },
        ].map(({ title, value, icon }) => (
          <AdminCard className="p-1" key={title}>
            <div className="flex items-center gap-4">
              <StatisticIcon icon={icon} />
              <AdminStatistic title={title} value={value} />
            </div>
          </AdminCard>
        ))}
      </div>

      <p className="text-foreground-muted text-sm">
        {stats.calls_this_week.toLocaleString()} calls this week ·{' '}
        {stats.calls_this_month.toLocaleString()} this month
      </p>

      <div className="grid grid-cols-1 gap-6 2xl:grid-cols-2">
        <AdminCard title="Usage by tool">
          {tools ? (
            <AdminTable
              dataSource={tools}
              columns={toolColumns}
              rowKey="tool_name"
              pagination={false}
              emptyText="No MCP calls recorded"
              size="small"
            />
          ) : (
            <p role="alert" className="text-sm text-red-500">
              Failed to load tool breakdown.
            </p>
          )}
        </AdminCard>
        <AdminCard title="Daily activity">
          {daily ? (
            <AdminTable
              dataSource={daily}
              columns={dailyColumns}
              rowKey="date"
              pagination={false}
              emptyText="No daily activity recorded"
              size="small"
            />
          ) : (
            <p role="alert" className="text-sm text-red-500">
              Failed to load daily activity.
            </p>
          )}
        </AdminCard>
      </div>

      <AdminCard title="Recent events">
        <form method="get" className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <label className="text-sm">
            <span>Tool</span>
            <input
              name="tool"
              defaultValue={filters.tool}
              className="border-border bg-surface text-foreground mt-1 w-full rounded border px-3 py-2"
              placeholder="search_jobs"
            />
          </label>
          <label className="text-sm">
            <span>Status</span>
            <select
              name="status"
              defaultValue={filters.status}
              className="border-border bg-surface text-foreground mt-1 w-full rounded border px-3 py-2"
            >
              <option value="">All</option>
              <option value="success">Success</option>
              <option value="failure">Failure</option>
            </select>
          </label>
          <label className="text-sm">
            <span>From</span>
            <input
              type="date"
              name="date_from"
              defaultValue={filters.dateFrom}
              className="border-border bg-surface text-foreground mt-1 w-full rounded border px-3 py-2"
            />
          </label>
          <label className="text-sm">
            <span>To</span>
            <input
              type="date"
              name="date_to"
              defaultValue={filters.dateTo}
              className="border-border bg-surface text-foreground mt-1 w-full rounded border px-3 py-2"
            />
          </label>
          <div className="flex flex-wrap items-end gap-2">
            <button
              type="submit"
              className="bg-accent text-on-accent hover:bg-accent-hover rounded px-4 py-2 text-sm font-medium"
            >
              Filter
            </button>
            <a
              href="/admin/agent-usage"
              className="border-border text-foreground-secondary hover:bg-surface-subtle rounded border px-4 py-2 text-sm"
            >
              Reset
            </a>
          </div>
        </form>
        {events ? (
          <AdminTable
            dataSource={events.items}
            columns={eventColumns}
            rowKey="id"
            pagination={
              events.total_pages > 1
                ? {
                    current: events.page,
                    pageSize: events.page_size,
                    total: events.total,
                    buildPageUrl: buildEventsUrl,
                  }
                : false
            }
            emptyText="No MCP events match these filters"
            size="small"
          />
        ) : (
          <p role="alert" className="text-sm text-red-500">
            Failed to load recent MCP events.
          </p>
        )}
      </AdminCard>
    </div>
  );
}
