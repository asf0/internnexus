import type { AdminColumn } from '@/components/admin/ui';
import { formatDateTime, formatDateShort, addUtmParams } from './utils';
import type { ClickStats, ClickByDay, JobClick, ClicksByUser } from './types';

export function createTopJobsColumns(): AdminColumn<ClickStats['top_jobs'][number]>[] {
  return [
    {
      title: 'Job Title',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      priority: 'primary',
    },
    {
      title: 'Company',
      dataIndex: 'company',
      key: 'company',
      ellipsis: true,
      priority: 'secondary',
    },
    {
      title: 'Clicks',
      dataIndex: 'click_count',
      key: 'click_count',
      priority: 'secondary',
      render: (count: number) => (
        <span className="text-accent font-semibold">{count.toLocaleString()}</span>
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
      priority: 'primary',
      render: (date: string) => (
        <span className="text-foreground-secondary">{formatDateShort(date)}</span>
      ),
    },
    {
      title: 'Clicks',
      dataIndex: 'clicks',
      key: 'clicks',
      priority: 'secondary',
      render: (clicks: number) => (
        <div className="flex items-center gap-2">
          <div
            className="bg-accent h-2 rounded"
            style={{
              width: `${Math.min(100, (clicks / maxClicks) * 100)}%`,
              minWidth: clicks > 0 ? '4px' : '0px',
            }}
          />
          <span className="text-foreground font-semibold">{clicks.toLocaleString()}</span>
        </div>
      ),
    },
    {
      title: 'Unique Users',
      dataIndex: 'unique_users',
      key: 'unique_users',
      priority: 'detail',
      render: (value?: number) => (
        <span className="text-foreground-secondary">{(value ?? 0).toLocaleString()}</span>
      ),
    },
    {
      title: 'Unique Jobs',
      dataIndex: 'unique_jobs',
      key: 'unique_jobs',
      priority: 'detail',
      render: (value?: number) => (
        <span className="text-foreground-secondary">{(value ?? 0).toLocaleString()}</span>
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
      priority: 'primary',
      render: (value: string) => <span className="text-foreground">{value || 'unknown'}</span>,
    },
    {
      title: 'Clicks',
      dataIndex: 'click_count',
      key: 'click_count',
      width: 120,
      priority: 'secondary',
      render: (count: number) => (
        <span className="text-accent font-semibold">{count.toLocaleString()}</span>
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
      priority: 'primary',
      render: (_title: string, record: JobClick) => {
        if (record.apply_url) {
          return (
            <a
              href={addUtmParams(record.apply_url)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent hover:text-accent-hover hover:underline"
            >
              {record.job_title}
            </a>
          );
        }
        return <span className="text-foreground">{record.job_title}</span>;
      },
    },
    {
      title: 'Company',
      dataIndex: 'company',
      key: 'company',
      ellipsis: true,
      priority: 'secondary',
      render: (company: string) => <span className="text-foreground-muted">{company}</span>,
    },
    {
      title: 'Clicked At',
      dataIndex: 'clicked_at',
      key: 'clicked_at',
      width: 160,
      priority: 'secondary',
      render: (date: string) => (
        <span className="text-foreground-muted text-sm">{formatDateTime(date)}</span>
      ),
    },
    {
      title: 'User',
      dataIndex: 'user_id',
      key: 'user_id',
      width: 180,
      priority: 'detail',
      render: (_: unknown, record: JobClick) => (
        <span className="text-foreground-muted text-sm">{record.user_email || 'Anonymous'}</span>
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
      priority: 'primary',
      render: (email: string | null) => (
        <span className="text-foreground">{email || 'Anonymous'}</span>
      ),
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      priority: 'secondary',
      render: (name: string | null) => (
        <span className="text-foreground-muted">{name || 'Anonymous'}</span>
      ),
    },
    {
      title: 'Click Count',
      dataIndex: 'click_count',
      key: 'click_count',
      width: 120,
      priority: 'secondary',
      render: (count: number) => (
        <span className="text-accent font-semibold">{count.toLocaleString()}</span>
      ),
    },
  ];
}
