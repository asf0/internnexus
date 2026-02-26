"use client";

import { Card, Statistic, Table, Typography, Spin, Alert } from "antd";
import {
  MousePointer,
  TrendingUp,
  Calendar,
  CalendarDays,
  BarChart3,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchClicksByUser } from "@/app/actions/admin";
import DayDetailModal from "@/components/admin/DayDetailModal";

const { Title } = Typography;

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
  readonly daily_breakdown_14d: Array<{ readonly date: string; readonly clicks: number; readonly unique_users: number }>;
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

// Icon wrapper component for Ant Design compatibility
function StatisticIcon({ icon: Icon }: { icon: LucideIcon }) {
  return (
    <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-blue-50 dark:bg-blue-900/30">
      <Icon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
    </div>
  );
}

// Format date for display - uses UTC timezone for hydration safety
function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });
}

// Format date for chart display - uses UTC timezone for hydration safety
function formatDateShort(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

// Add UTM parameters to a URL
function addUtmParams(baseUrl: string, source = "internnexus"): string {
  try {
    const url = new URL(baseUrl);
    url.searchParams.set("utm_source", source);
    return url.toString();
  } catch {
    return baseUrl;
  }
}

export function ClicksClient({
  clickStats,
  clicksByDay,
  recentClicks,
}: ClicksClientProps) {
  // State for clicks by user data
  const [clicksByUser, setClicksByUser] = useState<ClicksByUser[]>([]);
  const [clicksByUserLoading, setClicksByUserLoading] = useState(true);
  const [clicksByUserError, setClicksByUserError] = useState<string | null>(null);

  // State for day detail modal
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

  // Fetch clicks by user on mount
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

  // Calculate max clicks for bar chart scaling
  const maxClicks = Math.max(...(clicksByDay?.map((d) => d.clicks) || [1]));

  // Top jobs table columns
  const topJobsColumns = [
    {
      title: "Job Title",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
    },
    {
      title: "Company",
      dataIndex: "company",
      key: "company",
      ellipsis: true,
    },
    {
      title: "Clicks",
      dataIndex: "click_count",
      key: "click_count",
      render: (count: number) => (
        <span className="font-semibold text-blue-600 dark:text-blue-400">
          {count.toLocaleString()}
        </span>
      ),
    },
  ];

  // Clicks by day table columns
  const clicksByDayColumns = [
    {
      title: "Date",
      dataIndex: "date",
      key: "date",
      render: (date: string) => (
        <span className="text-slate-700 dark:text-slate-300">
          {formatDateShort(date)}
        </span>
      ),
    },
    {
      title: "Clicks",
      dataIndex: "clicks",
      key: "clicks",
      render: (clicks: number) => (
        <div className="flex items-center gap-2">
          <div
            className="h-2 bg-blue-500 rounded"
            style={{
              width: `${Math.min(100, (clicks / maxClicks) * 100)}%`,
              minWidth: clicks > 0 ? "4px" : "0px",
            }}
          />
          <span className="font-semibold text-slate-900 dark:text-slate-100">
            {clicks.toLocaleString()}
          </span>
        </div>
      ),
    },
    {
      title: "Unique Users",
      dataIndex: "unique_users",
      key: "unique_users",
      render: (value?: number) => (
        <span className="text-slate-700 dark:text-slate-300">
          {(value ?? 0).toLocaleString()}
        </span>
      ),
    },
    {
      title: "Unique Jobs",
      dataIndex: "unique_jobs",
      key: "unique_jobs",
      render: (value?: number) => (
        <span className="text-slate-700 dark:text-slate-300">
          {(value ?? 0).toLocaleString()}
        </span>
      ),
    },
  ];

  const trafficColumns = [
    {
      title: "Value",
      dataIndex: "value",
      key: "value",
      ellipsis: true,
      render: (value: string) => (
        <span className="text-slate-900 dark:text-slate-100">{value || "unknown"}</span>
      ),
    },
    {
      title: "Clicks",
      dataIndex: "click_count",
      key: "click_count",
      width: 120,
      render: (count: number) => (
        <span className="font-semibold text-blue-600 dark:text-blue-400">
          {count.toLocaleString()}
        </span>
      ),
    },
  ];

  // Recent clicks table columns
  const recentClicksColumns = [
    {
      title: "Job Title",
      dataIndex: "job_title",
      key: "job_title",
      ellipsis: true,
      render: (title: string, record: JobClick) => {
        if (record.apply_url) {
          return (
            <a
              href={addUtmParams(record.apply_url)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
            >
              {title}
            </a>
          );
        }
        return <span className="text-slate-900 dark:text-slate-100">{title}</span>;
      },
    },
    {
      title: "Company",
      dataIndex: "company",
      key: "company",
      ellipsis: true,
      render: (company: string) => (
        <span className="text-slate-600 dark:text-slate-400">{company}</span>
      ),
    },
    {
      title: "Clicked At",
      dataIndex: "clicked_at",
      key: "clicked_at",
      width: 160,
      render: (date: string) => (
        <span className="text-slate-600 dark:text-slate-400 text-sm">
          {formatDateTime(date)}
        </span>
      ),
    },
    {
      title: "User",
      dataIndex: "user_id",
      key: "user_id",
      width: 180,
      render: (_: unknown, record: JobClick) => (
        <span className="text-slate-600 dark:text-slate-400 text-sm">
          {record.user_email || "Anonymous"}
        </span>
      ),
    },
  ];

  // Top users by clicks table columns
  const topUsersColumns = [
    {
      title: "User Email",
      dataIndex: "email",
      key: "email",
      ellipsis: true,
      render: (email: string | null) => (
        <span className="text-slate-900 dark:text-slate-100">
          {email || "Anonymous"}
        </span>
      ),
    },
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      ellipsis: true,
      render: (name: string | null) => (
        <span className="text-slate-600 dark:text-slate-400">
          {name || "Anonymous"}
        </span>
      ),
    },
    {
      title: "Click Count",
      dataIndex: "click_count",
      key: "click_count",
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Title level={2} className="!mb-1 !text-slate-900 dark:!text-slate-100">
            Click Analytics
          </Title>
          <p className="text-slate-600 dark:text-slate-400">
            Track job click activity and engagement metrics
          </p>
        </div>
      </div>

      {/* Row 1: Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card
          className="shadow-sm"
          styles={{ body: { padding: "20px" } }}
        >
          <div className="flex items-center gap-4">
            <StatisticIcon icon={MousePointer} />
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Total Clicks</span>}
              value={clickStats.total_clicks}
              styles={{ content: { color: "#E6E1E5" } }}
            />
          </div>
        </Card>

        <Card
          className="shadow-sm"
          styles={{ body: { padding: "20px" } }}
        >
          <div className="flex items-center gap-4">
            <StatisticIcon icon={TrendingUp} />
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Clicks Today</span>}
              value={clickStats.clicks_today}
              styles={{ content: { color: "#005AC1" } }}
            />
          </div>
        </Card>

        <Card
          className="shadow-sm"
          styles={{ body: { padding: "20px" } }}
        >
          <div className="flex items-center gap-4">
            <StatisticIcon icon={Calendar} />
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Clicks This Week</span>}
              value={clickStats.clicks_this_week}
              styles={{ content: { color: "#E6E1E5" } }}
            />
          </div>
        </Card>

        <Card
          className="shadow-sm"
          styles={{ body: { padding: "20px" } }}
        >
          <div className="flex items-center gap-4">
            <StatisticIcon icon={CalendarDays} />
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Clicks This Month</span>}
              value={clickStats.clicks_this_month}
              styles={{ content: { color: "#E6E1E5" } }}
            />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <Statistic
            title={<span className="text-slate-600 dark:text-slate-400">Clicks (24h)</span>}
            value={clickStats.clicks_last_24h}
          />
        </Card>
        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <Statistic
            title={<span className="text-slate-600 dark:text-slate-400">Unique Users</span>}
            value={clickStats.unique_users_total}
          />
        </Card>
        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <Statistic
            title={<span className="text-slate-600 dark:text-slate-400">Anonymous Clicks</span>}
            value={clickStats.anonymous_clicks_total}
          />
        </Card>
        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <Statistic
            title={<span className="text-slate-600 dark:text-slate-400">Avg/Day (30d)</span>}
            value={clickStats.avg_clicks_per_day_30d}
            precision={2}
          />
        </Card>
      </div>

      {/* Row 2: Clicks by Day Chart (as table) */}
      <Card
        title={
          <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
            <BarChart3 className="w-5 h-5" />
            Clicks by Day (Last 30 Days)
          </span>
        }
        className="shadow-sm"
      >
        <Table
          dataSource={clicksByDay || []}
          columns={clicksByDayColumns}
          rowKey="date"
          pagination={false}
          size="small"
          scroll={{ y: 300 }}
          locale={{ emptyText: "No click data available" }}
          onRow={(record) => ({
            onClick: () => openDayModal(record.date),
            style: { cursor: "pointer" },
          })}
        />
      </Card>

      {/* Row 3: Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Jobs by Clicks */}
        <Card
          title={
            <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
              <TrendingUp className="w-5 h-5" />
              Top Jobs by Clicks
            </span>
          }
          className="shadow-sm"
        >
          <Table
            dataSource={clickStats.top_jobs}
            columns={topJobsColumns}
            rowKey="job_id"
            pagination={false}
            size="small"
            locale={{ emptyText: "No clicks recorded yet" }}
          />
        </Card>

        {/* Recent Clicks */}
        <Card
          title={
            <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
              <MousePointer className="w-5 h-5" />
              Recent Clicks
            </span>
          }
          className="shadow-sm"
        >
          <Table
            dataSource={recentClicks?.items || []}
            columns={recentClicksColumns}
            rowKey="id"
            pagination={false}
            size="small"
            scroll={{ x: 700 }}
            locale={{ emptyText: "No recent clicks" }}
          />
          {recentClicks && recentClicks.total > 50 && (
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700 text-center">
              <span className="text-sm text-slate-500">
                Showing 50 of {recentClicks.total.toLocaleString()} total clicks
              </span>
            </div>
          )}
        </Card>
      </div>

      {/* Row 4: Top Users by Clicks */}
      <Card
        title={
          <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
            <Users className="w-5 h-5" />
            Top Users by Clicks
          </span>
        }
        className="shadow-sm"
      >
        {clicksByUserError && (
          <Alert
            type="error"
            message={clicksByUserError}
            className="mb-4"
          />
        )}
        {clicksByUserLoading ? (
          <div className="flex justify-center py-8">
            <Spin />
          </div>
        ) : (
          <Table
            dataSource={clicksByUser}
            columns={topUsersColumns}
            rowKey={(record) => record.user_id || "anonymous"}
            pagination={false}
            size="small"
            locale={{ emptyText: "No user click data available" }}
          />
        )}
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card
          title={<span className="text-slate-900 dark:text-slate-100">Top Sources</span>}
          className="shadow-sm"
        >
          <Table
            dataSource={clickStats.top_sources || []}
            columns={trafficColumns}
            rowKey={(record) => `source-${record.value}`}
            pagination={false}
            size="small"
          />
        </Card>
        <Card
          title={<span className="text-slate-900 dark:text-slate-100">Top Mediums</span>}
          className="shadow-sm"
        >
          <Table
            dataSource={clickStats.top_mediums || []}
            columns={trafficColumns}
            rowKey={(record) => `medium-${record.value}`}
            pagination={false}
            size="small"
          />
        </Card>
        <Card
          title={<span className="text-slate-900 dark:text-slate-100">Top Campaigns</span>}
          className="shadow-sm"
        >
          <Table
            dataSource={clickStats.top_campaigns || []}
            columns={trafficColumns}
            rowKey={(record) => `campaign-${record.value}`}
            pagination={false}
            size="small"
          />
        </Card>
      </div>

      {/* Day Detail Modal */}
      <DayDetailModal
        isOpen={isDayModalOpen}
        onClose={closeDayModal}
        date={selectedDate}
      />
    </div>
  );
}
