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
            <StatisticIcon icon={Calendar} />
            <AdminStatistic title="Clicks This Week" value={clickStats.clicks_this_week} />
          </div>
        </AdminCard>

        <AdminCard className="p-5">
          <div className="flex items-center gap-4">
            <StatisticIcon icon={CalendarDays} />
            <AdminStatistic title="Clicks This Month" value={clickStats.clicks_this_month} />
          </div>
        </AdminCard>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <AdminCard className="p-5">
          <AdminStatistic title="Clicks (24h)" value={clickStats.clicks_last_24h} />
        </AdminCard>
        <AdminCard className="p-5">
          <AdminStatistic title="Unique Users" value={clickStats.unique_users_total} />
        </AdminCard>
        <AdminCard className="p-5">
          <AdminStatistic title="Anonymous Clicks" value={clickStats.anonymous_clicks_total} />
        </AdminCard>
        <AdminCard className="p-5">
          <AdminStatistic
            title="Avg/Day (30d)"
            value={clickStats.avg_clicks_per_day_30d}
            precision={2}
          />
        </AdminCard>
      </div>
    </>
  );
}
