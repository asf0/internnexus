"use client";

import { Card, Statistic, Table, Tag, Typography, Row, Col } from "antd";
import {
  PlayCircle,
  CheckCircle,
  XCircle,
  Clock,
  Activity,
  AlertCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const { Title } = Typography;

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

function StatisticIcon({ icon: Icon }: { readonly icon: LucideIcon }) {
  return (
    <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-blue-50 dark:bg-blue-900/30">
      <Icon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
    </div>
  );
}

function formatDate(dateString: string | null): string {
  if (!dateString) return "-";
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

function formatStep(step: string | null): string {
  if (!step) return "-";
  return step
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function PipelineRunsClient({
  pipelineStats,
  latestRun,
  pipelineRuns,
  statusFilter,
  currentPage,
}: PipelineRunsClientProps) {
  const columns = [
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 120,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: "Started At",
      dataIndex: "started_at",
      key: "started_at",
      width: 180,
      render: (date: string) => (
        <span className="text-slate-700 dark:text-slate-300">
          {formatDate(date)}
        </span>
      ),
    },
    {
      title: "Completed At",
      dataIndex: "completed_at",
      key: "completed_at",
      width: 180,
      render: (date: string | null) => (
        <span className="text-slate-700 dark:text-slate-300">
          {formatDate(date)}
        </span>
      ),
    },
    {
      title: "Step Completed",
      dataIndex: "step_completed",
      key: "step_completed",
      ellipsis: true,
      render: (step: string | null) => (
        <span className="text-slate-700 dark:text-slate-300">
          {formatStep(step)}
        </span>
      ),
    },
    {
      title: "Error",
      dataIndex: "error_message",
      key: "error_message",
      ellipsis: true,
      render: (error: string | null, record: PipelineRun) => {
        if (!error) return <span className="text-slate-400">-</span>;
        return (
          <div className="max-w-xs">
            <span className="text-red-600 dark:text-red-400 text-sm">
              {record.error_step && (
                <strong>[{formatStep(record.error_step)}]</strong>
              )} {error}
            </span>
          </div>
        );
      },
    },
  ];

  const statusOptions = [
    { label: "All", value: "" },
    { label: "Running", value: "running" },
    { label: "Completed", value: "completed" },
    { label: "Failed", value: "failed" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <div>
          <Title level={2} className="!mb-1 !text-slate-900 dark:!text-slate-100">
            Pipeline Runs
          </Title>
          <p className="text-slate-600 dark:text-slate-400">
            Monitor job ingestion pipeline execution history
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <div className="flex items-center gap-4">
            <StatisticIcon icon={Activity} />
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Total Runs</span>}
              value={pipelineStats.total_runs}
              styles={{ content: { color: "#E6E1E5" } }}
            />
          </div>
        </Card>

        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-green-50 dark:bg-green-900/30">
              <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Completed</span>}
              value={pipelineStats.completed}
              styles={{ content: { color: "#16a34a" } }}
            />
          </div>
        </Card>

        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-red-50 dark:bg-red-900/30">
              <XCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Failed</span>}
              value={pipelineStats.failed}
              styles={{ content: { color: "#dc2626" } }}
            />
          </div>
        </Card>

        <Card className="shadow-sm" styles={{ body: { padding: "20px" } }}>
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-blue-50 dark:bg-blue-900/30">
              <PlayCircle className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <Statistic
              title={<span className="text-slate-600 dark:text-slate-400">Currently Running</span>}
              value={pipelineStats.running}
              styles={{ content: { color: "#005AC1" } }}
            />
          </div>
        </Card>
      </div>

      <Card
        title={
          <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
            <Clock className="w-5 h-5" />
            Latest Run Status
          </span>
        }
        className="shadow-sm"
      >
        {latestRun ? (
          <Row gutter={[24, 16]}>
            <Col xs={24} md={8}>
              <div className="space-y-2">
                <span className="text-slate-500 dark:text-slate-400 text-sm">Status</span>
                <div>
                  {latestRun.status === "running" ? (
                    <Tag color="processing" icon={<PlayCircle className="w-3 h-3 inline mr-1" />}>
                      Currently Running
                    </Tag>
                  ) : latestRun.status === "completed" ? (
                    <Tag color="success" icon={<CheckCircle className="w-3 h-3 inline mr-1" />}>
                      Last Successful
                    </Tag>
                  ) : (
                    <Tag color="error" icon={<XCircle className="w-3 h-3 inline mr-1" />}>
                      Last Failed
                    </Tag>
                  )}
                </div>
              </div>
            </Col>
            <Col xs={24} md={8}>
              <div className="space-y-2">
                <span className="text-slate-500 dark:text-slate-400 text-sm">
                  {latestRun.status === "running" ? "Started At" : "Completed At"}
                </span>
                <div className="text-slate-900 dark:text-slate-100 font-medium">
                  {latestRun.status === "running"
                    ? formatDate(latestRun.started_at)
                    : formatDate(latestRun.completed_at)}
                </div>
              </div>
            </Col>
            <Col xs={24} md={8}>
              <div className="space-y-2">
                <span className="text-slate-500 dark:text-slate-400 text-sm">
                  {latestRun.status === "running" ? "Current Step" : "Step Completed"}
                </span>
                <div className="text-slate-900 dark:text-slate-100 font-medium">
                  {formatStep(latestRun.step_completed)}
                </div>
              </div>
            </Col>
            {latestRun.status === "failed" && latestRun.error_message && (
              <Col xs={24}>
                <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-red-800 dark:text-red-200">
                        Error {latestRun.error_step && `in ${formatStep(latestRun.error_step)}`}
                      </p>
                      <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                        {latestRun.error_message}
                      </p>
                    </div>
                  </div>
                </div>
              </Col>
            )}
          </Row>
        ) : (
          <div className="text-center py-8 text-slate-500 dark:text-slate-400">
            No pipeline runs recorded yet
          </div>
        )}
      </Card>

      <Card
        title={
          <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
            <Activity className="w-5 h-5" />
            Pipeline Run History
          </span>
        }
        className="shadow-sm"
        extra={
          <div className="flex gap-2">
            {statusOptions.map((option) => (
              <a
                key={option.value}
                href={`/admin/pipeline?status=${option.value}`}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  statusFilter === option.value
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600"
                }`}
              >
                {option.label}
              </a>
            ))}
          </div>
        }
      >
        <Table
          dataSource={pipelineRuns?.items || []}
          columns={columns}
          rowKey="id"
          pagination={
            pipelineRuns && pipelineRuns.total_pages > 1
              ? {
                  current: currentPage,
                  pageSize: 20,
                  total: pipelineRuns.total,
                  showSizeChanger: false,
                  showTotal: (total) => `Total ${total} runs`,
                  itemRender: (page, type, originalElement) => {
                    if (type === "page") {
                      return (
                        <a
                          href={`/admin/pipeline?page=${page}&status=${statusFilter}`}
                          className="px-3 py-1"
                        >
                          {page}
                        </a>
                      );
                    }
                    if (type === "prev") {
                      return (
                        <a
                          href={`/admin/pipeline?page=${currentPage - 1}&status=${statusFilter}`}
                          className="px-3 py-1"
                        >
                          Previous
                        </a>
                      );
                    }
                    if (type === "next") {
                      return (
                        <a
                          href={`/admin/pipeline?page=${currentPage + 1}&status=${statusFilter}`}
                          className="px-3 py-1"
                        >
                          Next
                        </a>
                      );
                    }
                    return originalElement;
                  },
                }
              : false
          }
          size="middle"
          locale={{ emptyText: "No pipeline runs found" }}
        />
      </Card>
    </div>
  );
}
