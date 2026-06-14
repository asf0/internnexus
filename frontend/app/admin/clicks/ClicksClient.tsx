'use client';

import { MousePointer, TrendingUp, Calendar, CalendarDays, BarChart3, Users } from 'lucide-react';
import { useEffect, useState } from 'react';
import { fetchClicksByUser } from '@/app/actions/admin';
import { StatisticIcon } from '@/components/admin/StatisticIcon';
import { Alert, LoadingSpinner } from '@/components/ui';
import DayDetailModal from '@/components/admin/DayDetailModal';
import { AdminCard, AdminStatistic, AdminTable } from '@/components/admin/ui';
import type { AdminColumn } from '@/components/admin/ui';

interface ClickStats {
  readonly total_clicks: number;
  readonly clicks_today: number;
  readonly clicks_this_week: number;
  readonly clicks_this_month: number;
  readonly authenticated_clicks_total: number;
  readonly anonymous_clicks_total: number;
  readonly unique_users_total: number;
  readonly unique_jobs_total: number;
  readonly clicks_last_24h: number;
  readonly avg_clicks_per_day_30d: number;
  readonly top_sources: Array<{ readonly value: string; readonly click_count: number }>;
  readonly top_mediums: Array<{ readonly value: string; readonly click_count: number }>;
  readonly top_campaigns: Array<{ readonly value: string; readonly click_count: number }>;
  readonly clicks_by_hour_today: Array<{ readonly hour: number; readonly clicks: number }>;
  readonly daily_breakdown_14d: Array<{
    readonly date: string;
    readonly clicks: number;
    readonly unique_users: number;
  }>;
  readonly top_jobs: Array<{
    readonly job_id: string;
    readonly title: string;
    readonly company: string;
    readonly click_count: number;
  }>;
}

interface ClickByDay {
  readonly date: string;
  readonly clicks: number;
  readonly unique_users?: number;
  readonly unique_jobs?: number;
}

interface JobClick {
  readonly id: string;
  readonly job_id: string;
  readonly job_title: string;
  readonly company: string;
  readonly apply_url: string | null;
  readonly user_id: string | null;
  readonly user_email: string | null;
  readonly user_name: string | null;
  readonly clicked_at: string;
  readonly utm_source: string;
  readonly utm_medium: string | null;
  readonly utm_campaign: string | null;
}

interface ClicksByUser {
  readonly user_id: string | null;
  readonly email: string | null;
  readonly name: string | null;
  readonly click_count: number;
}

interface ClicksListResponse {
  readonly items: JobClick[];
  readonly total: number;
  readonly page: number;
  readonly page_size: number;
  readonly total_pages: number;
}

interface ClicksClientProps {
  readonly clickStats: ClickStats;
  readonly clicksByDay: Array<ClickByDay> | null;
  readonly recentClicks: ClicksListResponse | null;
}

function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
  });
}

function formatDateShort(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  });
}

function addUtmParams(baseUrl: string, source = 'internnexus'): string {
  try {
    const url = new URL(baseUrl);
    url.searchParams.set('utm_source', source);
    return url.toString();
  } catch {
    return baseUrl;
  }
}

export function ClicksClient({ clickStats, clicksByDay, recentClicks }: ClicksClientProps) {
  const [clicksByUser, setClicksByUser] = useState<ClicksByUser[]>([]);
  const [clicksByUserLoading, setClicksByUserLoading] = useState(true);
  const [clicksByUserError, setClicksByUserError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [isDayModalOpen, setIsDayModalOpen] = useState(false);

  const openDayModal = (date: string) => {
    setSelectedDate(date);
    setIsDayModalOpen(true);
  };

  const closeDayModal = () => {
    setIsDayModalOpen(false);
    setSelectedDate(null);
  };

  useEffect(() => {
    async function loadClicksByUser() {
      setClicksByUserLoading(true);
      setClicksByUserError(null);
      const result = await fetchClicksByUser(20);
      if (result.error) {
        setClicksByUserError(result.error);
      } else if (result.data) {
        setClicksByUser(result.data);
      }
      setClicksByUserLoading(false);
    }
    loadClicksByUser();
  }, []);

  const maxClicks = Math.max(...(clicksByDay?.map((d) => d.clicks) || [1]));

  const topJobsColumns: AdminColumn<(typeof clickStats.top_jobs)[number]>[] = [
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

  const clicksByDayColumns: AdminColumn<ClickByDay>[] = [
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

  const trafficColumns: AdminColumn<{ value: string; click_count: number }>[] = [
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

  const recentClicksColumns: AdminColumn<JobClick>[] = [
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

  const topUsersColumns: AdminColumn<ClicksByUser>[] = [
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Click Analytics</h1>
          <p className="text-slate-600 dark:text-slate-400">
            Track job click activity and engagement metrics
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <StatisticIcon icon={MousePointer} />
            <AdminStatistic
              title={<span className="text-slate-600 dark:text-slate-400">Total Clicks</span>}
              value={clickStats.total_clicks}
            />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <StatisticIcon icon={TrendingUp} />
            <AdminStatistic
              title={<span className="text-slate-600 dark:text-slate-400">Clicks Today</span>}
              value={clickStats.clicks_today}
              valueClassName="text-blue-600 dark:text-blue-400"
            />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <StatisticIcon icon={Calendar} />
            <AdminStatistic
              title={<span className="text-slate-600 dark:text-slate-400">Clicks This Week</span>}
              value={clickStats.clicks_this_week}
            />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <StatisticIcon icon={CalendarDays} />
            <AdminStatistic
              title={<span className="text-slate-600 dark:text-slate-400">Clicks This Month</span>}
              value={clickStats.clicks_this_month}
            />
          </div>
        </AdminCard>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <AdminCard className="p-5">
          <AdminStatistic
            title={<span className="text-slate-600 dark:text-slate-400">Clicks (24h)</span>}
            value={clickStats.clicks_last_24h}
          />
        </AdminCard>
        <AdminCard className="p-5">
          <AdminStatistic
            title={<span className="text-slate-600 dark:text-slate-400">Unique Users</span>}
            value={clickStats.unique_users_total}
          />
        </AdminCard>
        <AdminCard className="p-5">
          <AdminStatistic
            title={<span className="text-slate-600 dark:text-slate-400">Anonymous Clicks</span>}
            value={clickStats.anonymous_clicks_total}
          />
        </AdminCard>
        <AdminCard className="p-5">
          <AdminStatistic
            title={<span className="text-slate-600 dark:text-slate-400">Avg/Day (30d)</span>}
            value={clickStats.avg_clicks_per_day_30d}
            precision={2}
          />
        </AdminCard>
      </div>

      <AdminCard
        title={
          <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
            <BarChart3 className="h-5 w-5" />
            Clicks by Day (Last 30 Days)
          </span>
        }
      >
        <AdminTable
          dataSource={clicksByDay || []}
          columns={clicksByDayColumns}
          rowKey="date"
          pagination={false}
          size="small"
          scroll={{ y: 300 }}
          emptyText="No click data available"
          onRow={(record) => ({
            onClick: () => openDayModal(record.date),
            className: 'cursor-pointer',
          })}
        />
      </AdminCard>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <AdminCard
          title={
            <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
              <TrendingUp className="h-5 w-5" />
              Top Jobs by Clicks
            </span>
          }
        >
          <AdminTable
            dataSource={clickStats.top_jobs}
            columns={topJobsColumns}
            rowKey="job_id"
            pagination={false}
            size="small"
            emptyText="No clicks recorded yet"
          />
        </AdminCard>

        <AdminCard
          title={
            <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
              <MousePointer className="h-5 w-5" />
              Recent Clicks
            </span>
          }
        >
          <AdminTable
            dataSource={recentClicks?.items || []}
            columns={recentClicksColumns}
            rowKey="id"
            pagination={false}
            size="small"
            scroll={{ x: 700 }}
            emptyText="No recent clicks"
          />
          {recentClicks && recentClicks.total > 50 && (
            <div className="mt-4 border-t border-slate-200 pt-4 text-center dark:border-slate-700">
              <span className="text-sm text-slate-500">
                Showing 50 of {recentClicks.total.toLocaleString()} total clicks
              </span>
            </div>
          )}
        </AdminCard>
      </div>

      <AdminCard
        title={
          <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
            <Users className="h-5 w-5" />
            Top Users by Clicks
          </span>
        }
      >
        {clicksByUserError && (
          <Alert type="error" className="mb-4">
            {clicksByUserError}
          </Alert>
        )}
        {clicksByUserLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner />
          </div>
        ) : (
          <AdminTable
            dataSource={clicksByUser}
            columns={topUsersColumns}
            rowKey={(record) => record.user_id || 'anonymous'}
            pagination={false}
            size="small"
            emptyText="No user click data available"
          />
        )}
      </AdminCard>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <AdminCard title={<span className="text-slate-900 dark:text-slate-100">Top Sources</span>}>
          <AdminTable
            dataSource={clickStats.top_sources || []}
            columns={trafficColumns}
            rowKey={(record) => `source-${record.value}`}
            pagination={false}
            size="small"
          />
        </AdminCard>
        <AdminCard title={<span className="text-slate-900 dark:text-slate-100">Top Mediums</span>}>
          <AdminTable
            dataSource={clickStats.top_mediums || []}
            columns={trafficColumns}
            rowKey={(record) => `medium-${record.value}`}
            pagination={false}
            size="small"
          />
        </AdminCard>
        <AdminCard
          title={<span className="text-slate-900 dark:text-slate-100">Top Campaigns</span>}
        >
          <AdminTable
            dataSource={clickStats.top_campaigns || []}
            columns={trafficColumns}
            rowKey={(record) => `campaign-${record.value}`}
            pagination={false}
            size="small"
          />
        </AdminCard>
      </div>

      <DayDetailModal isOpen={isDayModalOpen} onClose={closeDayModal} date={selectedDate} />
    </div>
  );
}
