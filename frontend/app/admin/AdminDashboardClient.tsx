"use client";

import { Card, Statistic, Table, Tag, Row, Col, Typography } from "antd";
import {
  Briefcase,
  Building2,
  MousePointer,
  Activity,
  CheckCircle,
  PlayCircle,
  Clock,
  TrendingUp,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const { Title } = Typography;

interface JobStats {
  readonly total_jobs: number;
  readonly active_jobs: number;
  readonly total_companies: number;
  readonly jobs_by_category: Record<string, number>;
}

interface ClickStats {
  readonly total_clicks: number;
  readonly clicks_today: number;
  readonly clicks_this_week: number;
  readonly clicks_this_month: number;
  readonly top_jobs: ReadonlyArray<{
    readonly job_id: string;
    readonly title: string;
    readonly company: string;
    readonly click_count: number;
  }>;
}

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

interface AdminDashboardClientProps {
  readonly jobStats: JobStats;
  readonly clickStats: ClickStats;
  readonly pipelineStats: PipelineStats;
  readonly latestRun: PipelineRun | null;
}

function StatisticIcon({ icon: Icon }: { icon: LucideIcon }) {
  return (
    <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-blue-50 dark:bg-blue-900/30">
      <Icon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
    </div>
  );
}

function formatDate(dateString: string | null): string {
  if (!dateString) return "Never";
  return new Date(dateString).toLocaleString("en-US", {
    timeZone: "UTC",
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getStatusColor(status: string): string {
  switch (status) {
    case "completed":
      return "green";
    case "running":
      return "blue";
    case "failed":
      return "red";
    default:
      return "default";
  }
}

export default function AdminDashboardClient({
  jobStats,
  clickStats,
  pipelineStats,
  latestRun,
}: AdminDashboardClientProps) {
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

  const categoryColumns = [
    {
      title: "Category",
      dataIndex: "category",
      key: "category",
      render: (category: string) => <Tag color="blue">{category}</Tag>,
    },
    {
      title: "Jobs",
      dataIndex: "count",
      key: "count",
      render: (count: number) => (
        <span className="font-semibold">{count.toLocaleString()}</span>
      ),
    },
  ];

  const categoryData = Object.entries(jobStats.jobs_by_category)
    .map(([category, count]) => ({
      category,
      count,
    }))
    .sort((a, b) => b.count - a.count);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Title level={2} className="!mb-1 !text-slate-900 dark:!text-slate-100">
            Admin Dashboard
          </Title>
          <p className="text-slate-600 dark:text-slate-400">
            Overview of system statistics and activity
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <div className="flex items-center gap-4">
            <StatisticIcon icon={Briefcase} />
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Total Jobs</span>}
              value={jobStats.total_jobs}
              styles={{ content: { color: "#E6E1E5" } }}
            />
          </div>
        </Card>

        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <div className="flex items-center gap-4">
            <StatisticIcon icon={CheckCircle} />
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Active Jobs</span>}
              value={jobStats.active_jobs}
              styles={{ content: { color: "#16a34a" } }}
            />
          </div>
        </Card>

        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <div className="flex items-center gap-4">
            <StatisticIcon icon={Building2} />
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Total Companies</span>}
              value={jobStats.total_companies}
              styles={{ content: { color: "#E6E1E5" } }}
            />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <div className="flex items-center gap-4">
            <StatisticIcon icon={MousePointer} />
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Total Clicks</span>}
              value={clickStats.total_clicks}
              styles={{ content: { color: "#E6E1E5" } }}
            />
          </div>
        </Card>

        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <div className="flex items-center gap-4">
            <StatisticIcon icon={TrendingUp} />
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Clicks Today</span>}
              value={clickStats.clicks_today}
              styles={{ content: { color: "#005AC1" } }}
            />
          </div>
        </Card>

        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <div className="flex items-center gap-4">
            <StatisticIcon icon={Activity} />
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Clicks This Week</span>}
              value={clickStats.clicks_this_week}
              styles={{ content: { color: "#E6E1E5" } }}
            />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card
          title={
            <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
              <PlayCircle className="w-5 h-5" />
              Pipeline Status
            </span>
          }
          className="shadow-sm"
        >
          <Row gutter={[16, 16]}>
            <Col span={8}>
              <Statistic
                title={<span className="text-slate-600 dark:text-slate-400">Total Runs</span>}
                value={pipelineStats.total_runs}
                styles={{ content: { fontSize: "24px" } }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title={<span className="text-slate-600 dark:text-slate-400">Completed</span>}
                value={pipelineStats.completed}
                styles={{ content: { fontSize: "24px", color: "#16a34a" } }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title={<span className="text-slate-600 dark:text-slate-400">Failed</span>}
                value={pipelineStats.failed}
                styles={{ content: { fontSize: "24px", color: "#dc2626" } }}
              />
            </Col>
          </Row>
          {pipelineStats.running > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <Tag color="processing" icon={<PlayCircle className="w-3 h-3 inline mr-1" />}>
                {pipelineStats.running} currently running
              </Tag>
            </div>
          )}
        </Card>

        <Card
          title={
            <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
              <Clock className="w-5 h-5" />
              Last Run Status
            </span>
          }
          className="shadow-sm"
        >
          {latestRun ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-slate-600 dark:text-slate-400">Status:</span>
                <Tag color={getStatusColor(latestRun.status)}>
                  {latestRun.status.toUpperCase()}
                </Tag>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600 dark:text-slate-400">Started:</span>
                <span className="text-slate-900 dark:text-slate-100">
                  {formatDate(latestRun.started_at)}
                </span>
              </div>
              {latestRun.completed_at && (
                <div className="flex items-center justify-between">
                  <span className="text-slate-600 dark:text-slate-400">Completed:</span>
                  <span className="text-slate-900 dark:text-slate-100">
                    {formatDate(latestRun.completed_at)}
                  </span>
                </div>
              )}
              {latestRun.error_message && (
                <div className="mt-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  <p className="text-sm text-red-600 dark:text-red-400">
                    <strong>Error:</strong> {latestRun.error_message}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-4 text-slate-500 dark:text-slate-400">
              No pipeline runs recorded yet
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
            dataSource={clickStats.top_jobs.slice(0, 5)}
            columns={topJobsColumns}
            rowKey="job_id"
            pagination={false}
            size="small"
            locale={{ emptyText: "No clicks recorded yet" }}
          />
        </Card>

        <Card
          title={
            <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
              <Briefcase className="w-5 h-5" />
              Jobs by Category
            </span>
          }
          className="shadow-sm"
        >
          <Table
            dataSource={categoryData}
            columns={categoryColumns}
            rowKey="category"
            pagination={false}
            size="small"
            locale={{ emptyText: "No categories found" }}
          />
        </Card>
      </div>
    </div>
  );
}
