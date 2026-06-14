import { MousePointer, TrendingUp, Calendar, CalendarDays } from 'lucide-react';
import { StatisticIcon } from '@/components/admin/StatisticIcon';
import { AdminCard, AdminStatistic } from '@/components/admin/ui';
import type { ClickStats } from './types';

interface ClickStatsCardsProps {
  readonly clickStats: ClickStats;
}

export function ClickStatsCards({ clickStats }: ClickStatsCardsProps) {
  return (
    <>
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
    </>
  );
}
