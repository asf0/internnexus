"use client";

import { useState, useEffect } from "react";
import { Calendar, MousePointerClick, Briefcase, Users, UserX, ExternalLink } from "lucide-react";
import { Card, Table, Spin, Alert, Statistic } from "antd";
import { Modal } from "@/components/modals";
import { IconContainer } from "@/components/ui";
import { fetchDayClickStats, type DayClickStats, type TopJobByClicks } from "@/app/actions/admin";

interface DayDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  date: string | null; // YYYY-MM-DD format
}

function addUtmParams(baseUrl: string, source = "internnexus"): string {
  try {
    const url = new URL(baseUrl);
    url.searchParams.set("utm_source", source);
    return url.toString();
  } catch {
    return baseUrl;
  }
}

function formatDate(dateString: string): string {
  const date = new Date(dateString + "T00:00:00");
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function DayDetailModal({
  isOpen,
  onClose,
  date,
}: DayDetailModalProps) {
  const [data, setData] = useState<DayClickStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch data when modal opens
  useEffect(() => {
    const loadData = async () => {
      if (!isOpen || !date) {
        setData(null);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      const result = await fetchDayClickStats(date);

      if (result.data) {
        setData(result.data);
      } else {
        setError(result.error || "Failed to load click statistics");
      }

      setIsLoading(false);
    };

    loadData();
  }, [isOpen, date]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setData(null);
      setError(null);
    }
  }, [isOpen]);

  // Calculate max clicks for hour bar scaling
  const maxHourClicks = data?.clicks_by_hour
    ? Math.max(...data.clicks_by_hour.map((h) => h.clicks), 1)
    : 1;

  // Table columns for top jobs
  const jobColumns = [
    {
      title: "Job Title",
      dataIndex: "title",
      key: "title",
      render: (_: unknown, record: TopJobByClicks) => (
        <a
          href={record.apply_url ? addUtmParams(record.apply_url) : "#"}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
        >
          {record.title}
          {record.apply_url && <ExternalLink className="w-3 h-3" />}
        </a>
      ),
    },
    {
      title: "Company",
      dataIndex: "company",
      key: "company",
      render: (company: string) => (
        <span className="text-slate-700 dark:text-md-on-surface-variant">
          {company}
        </span>
      ),
    },
    {
      title: "Click Count",
      dataIndex: "click_count",
      key: "click_count",
      align: "right" as const,
      render: (count: number) => (
        <span className="font-semibold text-slate-900 dark:text-md-on-surface">
          {count.toLocaleString()}
        </span>
      ),
    },
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-3">
          <IconContainer icon={Calendar} color="purple" />
          <span>{date ? formatDate(date) : "Day Details"}</span>
        </div>
      }
      size="xl"
    >
      <div className="space-y-6">
        {/* Loading State */}
        {isLoading && (
          <div className="flex justify-center py-12">
            <Spin size="large" />
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <Alert type="error" message={error} showIcon />
        )}

        {/* Content */}
        {data && !isLoading && !error && (
          <>
            {/* Stats Cards Row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <Card className="bg-slate-50 dark:bg-md-surface-container-high border-slate-200 dark:border-md-outline-variant">
                <Statistic
                  title={
                    <span className="flex items-center gap-2 text-slate-600 dark:text-md-on-surface-variant">
                      <MousePointerClick className="w-4 h-4" />
                      Total Clicks
                    </span>
                  }
                  value={data.total_clicks}
                  styles={{ content: { color: "#005AC1", fontWeight: 600 } }}
                />
              </Card>

              <Card className="bg-slate-50 dark:bg-md-surface-container-high border-slate-200 dark:border-md-outline-variant">
                <Statistic
                  title={
                    <span className="flex items-center gap-2 text-slate-600 dark:text-md-on-surface-variant">
                      <Briefcase className="w-4 h-4" />
                      Unique Jobs
                    </span>
                  }
                  value={data.unique_jobs}
                  styles={{ content: { color: "#005AC1", fontWeight: 600 } }}
                />
              </Card>

              <Card className="bg-slate-50 dark:bg-md-surface-container-high border-slate-200 dark:border-md-outline-variant">
                <Statistic
                  title={
                    <span className="flex items-center gap-2 text-slate-600 dark:text-md-on-surface-variant">
                      <Users className="w-4 h-4" />
                      Unique Users
                    </span>
                  }
                  value={data.unique_users}
                  styles={{ content: { color: "#005AC1", fontWeight: 600 } }}
                />
              </Card>

              <Card className="bg-slate-50 dark:bg-md-surface-container-high border-slate-200 dark:border-md-outline-variant">
                <Statistic
                  title={
                    <span className="flex items-center gap-2 text-slate-600 dark:text-md-on-surface-variant">
                      <UserX className="w-4 h-4" />
                      Anonymous Clicks
                    </span>
                  }
                  value={data.anonymous_clicks}
                  styles={{ content: { color: "#005AC1", fontWeight: 600 } }}
                />
              </Card>
            </div>

            {/* Clicks by Hour Section */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-md-on-surface uppercase tracking-wide">
                Clicks by Hour
              </h3>
              <div className="bg-slate-50 dark:bg-md-surface-container-high rounded-lg p-4 border border-slate-200 dark:border-md-outline-variant">
                <div className="grid grid-cols-12 lg:grid-cols-24 gap-1">
                  {Array.from({ length: 24 }, (_, hour) => {
                    const hourData = data.clicks_by_hour.find((h) => h.hour === hour);
                    const clicks = hourData?.clicks || 0;
                    const widthPercent = (clicks / maxHourClicks) * 100;

                    return (
                      <div
                        key={hour}
                        className="flex flex-col items-center"
                        title={`${hour}:00 - ${clicks} clicks`}
                      >
                        {/* Bar */}
                        <div className="w-full h-16 bg-slate-200 dark:bg-md-surface-container rounded-sm relative flex items-end">
                          <div
                            className="w-full bg-blue-500 dark:bg-blue-400 rounded-sm transition-all"
                            style={{ height: `${widthPercent}%` }}
                          />
                        </div>
                        {/* Hour label */}
                        <span className="text-xs text-slate-500 dark:text-md-on-surface-variant mt-1">
                          {hour}
                        </span>
                        {/* Click count */}
                        <span className="text-xs font-medium text-slate-700 dark:text-md-on-surface">
                          {clicks}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Top Jobs Table */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-md-on-surface uppercase tracking-wide">
                Top Jobs
              </h3>
              <Table
                dataSource={data.top_jobs.slice(0, 10)}
                columns={jobColumns}
                rowKey="job_id"
                pagination={false}
                size="small"
                className="[&_.ant-table]:bg-transparent [&_.ant-table-thead>tr>th]:bg-slate-100 [&_.ant-table-thead>tr>th]:dark:bg-md-surface-container-high [&_.ant-table-tbody>tr>td]:bg-white [&_.ant-table-tbody>tr>td]:dark:bg-md-surface-container"
              />
            </div>
          </>
        )}

        {/* Empty state when no date */}
        {!date && !isLoading && (
          <div className="text-center py-12 text-slate-500 dark:text-md-on-surface-variant">
            No date selected
          </div>
        )}
      </div>
    </Modal>
  );
}
