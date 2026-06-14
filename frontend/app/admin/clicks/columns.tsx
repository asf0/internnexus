import type { AdminColumn } from '@/components/admin/ui';
import { formatDateTime, formatDateShort, addUtmParams } from './utils';
import type { ClickStats, ClickByDay, JobClick, ClicksByUser } from './types';

export function createTopJobsColumns(): AdminColumn<ClickStats['top_jobs'][number]>[] {
  return [
    { title: 'Job Title', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: 'Company', dataIndex: 'company', key: 'company', ellipsis: true },
    {
      title: 'Clicks',
      dataIndex: 'click_count',
      key: 'click_count',
      render: (count: number) => (
        <span className="font-semibold text-blue-600 dark:text-blue-400">
          {count.toLocaleString()}
        </span>
      ),
    },
  ];
}

export function createClicksByDayColumns(maxClicks: number): AdminColumn<ClickByDay>[] {
  return [
    {
      title: 'Date',
      dataIndex: 'date',
      key: 'date',
      render: (date: string) => (
        <span className="text-slate-700 dark:text-slate-300">{formatDateShort(date)}</span>
      ),
    },
    {
      title: 'Clicks',
      dataIndex: 'clicks',
      key: 'clicks',
      render: (clicks: number) => (
        <div className="flex items-center gap-2">
          <div
            className="h-2 rounded bg-blue-500"
            style={{
              width: `${Math.min(100, (clicks / maxClicks) * 100)}%`,
              minWidth: clicks > 0 ? '4px' : '0px',
            }}
          />
          <span className="font-semibold text-slate-900 dark:text-slate-100">
            {clicks.toLocaleString()}
          </span>
        </div>
      ),
    },
    {
      title: 'Unique Users',
      dataIndex: 'unique_users',
      key: 'unique_users',
      render: (value?: number) => (
        <span className="text-slate-700 dark:text-slate-300">{(value ?? 0).toLocaleString()}</span>
      ),
    },
    {
      title: 'Unique Jobs',
      dataIndex: 'unique_jobs',
      key: 'unique_jobs',
      render: (value?: number) => (
        <span className="text-slate-700 dark:text-slate-300">{(value ?? 0).toLocaleString()}</span>
      ),
    },
  ];
}

export function createTrafficColumns(): AdminColumn<{ value: string; click_count: number }>[] {
  return [
    {
      title: 'Value',
      dataIndex: 'value',
      key: 'value',
      ellipsis: true,
      render: (value: string) => (
        <span className="text-slate-900 dark:text-slate-100">{value || 'unknown'}</span>
      ),
    },
    {
      title: 'Clicks',
      dataIndex: 'click_count',
      key: 'click_count',
      width: 120,
      render: (count: number) => (
        <span className="font-semibold text-blue-600 dark:text-blue-400">
          {count.toLocaleString()}
        </span>
      ),
    },
  ];
}

export function createRecentClicksColumns(): AdminColumn<JobClick>[] {
  return [
    {
      title: 'Job Title',
      dataIndex: 'job_title',
      key: 'job_title',
      ellipsis: true,
      render: (_title: string, record: JobClick) => {
        if (record.apply_url) {
          return (
            <a
              href={addUtmParams(record.apply_url)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 hover:underline dark:text-blue-400 dark:hover:text-blue-300"
            >
              {record.job_title}
            </a>
          );
        }
        return <span className="text-slate-900 dark:text-slate-100">{record.job_title}</span>;
      },
    },
    {
      title: 'Company',
      dataIndex: 'company',
      key: 'company',
      ellipsis: true,
      render: (company: string) => (
        <span className="text-slate-600 dark:text-slate-400">{company}</span>
      ),
    },
    {
      title: 'Clicked At',
      dataIndex: 'clicked_at',
      key: 'clicked_at',
      width: 160,
      render: (date: string) => (
        <span className="text-sm text-slate-600 dark:text-slate-400">{formatDateTime(date)}</span>
      ),
    },
    {
      title: 'User',
      dataIndex: 'user_id',
      key: 'user_id',
      width: 180,
      render: (_: unknown, record: JobClick) => (
        <span className="text-sm text-slate-600 dark:text-slate-400">
          {record.user_email || 'Anonymous'}
        </span>
      ),
    },
  ];
}

export function createTopUsersColumns(): AdminColumn<ClicksByUser>[] {
  return [
    {
      title: 'User Email',
      dataIndex: 'email',
      key: 'email',
      ellipsis: true,
      render: (email: string | null) => (
        <span className="text-slate-900 dark:text-slate-100">{email || 'Anonymous'}</span>
      ),
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (name: string | null) => (
        <span className="text-slate-600 dark:text-slate-400">{name || 'Anonymous'}</span>
      ),
    },
    {
      title: 'Click Count',
      dataIndex: 'click_count',
      key: 'click_count',
      width: 120,
      render: (count: number) => (
        <span className="font-semibold text-blue-600 dark:text-blue-400">
          {count.toLocaleString()}
        </span>
      ),
    },
  ];
}
