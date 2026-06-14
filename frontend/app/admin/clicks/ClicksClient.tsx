'use client';

import { useState } from 'react';
import { TrendingUp, MousePointer, BarChart3, Users } from 'lucide-react';
import DayDetailModal from '@/components/admin/DayDetailModal';
import { Alert, LoadingSpinner } from '@/components/ui';
import { AdminCard, AdminTable } from '@/components/admin/ui';
import { useClicksByUser } from './useClicksByUser';
import { ClickStatsCards } from './ClickStatsCards';
import {
  createTopJobsColumns,
  createClicksByDayColumns,
  createTrafficColumns,
  createRecentClicksColumns,
  createTopUsersColumns,
} from './columns';
import type { ClickStats, ClickByDay, ClicksListResponse } from './types';

interface ClicksClientProps {
  readonly clickStats: ClickStats;
  readonly clicksByDay: Array<ClickByDay> | null;
  readonly recentClicks: ClicksListResponse | null;
}

export function ClicksClient({ clickStats, clicksByDay, recentClicks }: ClicksClientProps) {
  const {
    clicksByUser,
    loading: clicksByUserLoading,
    error: clicksByUserError,
  } = useClicksByUser(20);
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

  const maxClicks = Math.max(...(clicksByDay?.map((d) => d.clicks) || [1]));

  const topJobsColumns = createTopJobsColumns();
  const clicksByDayColumns = createClicksByDayColumns(maxClicks);
  const trafficColumns = createTrafficColumns();
  const recentClicksColumns = createRecentClicksColumns();
  const topUsersColumns = createTopUsersColumns();

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

      <ClickStatsCards clickStats={clickStats} />

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
