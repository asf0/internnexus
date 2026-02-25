"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Table,
  Space,
  Input,
  Select,
  Tag,
  Form,
  Button,
  Row,
  Col,
  Card,
  Typography,
  Spin,
  message,
} from "antd";
import type { TableProps } from "antd";
import {
  SearchOutlined,
  ReloadOutlined,
  EyeOutlined,
  EditOutlined,
} from "@ant-design/icons";
import { Plus } from "lucide-react";
import Link from "next/link";
import {
  fetchJobs,
  bulkJobAction,
  type AdminJob,
  type PaginatedResponse,
} from "@/app/actions/admin";
import { BulkActionsBar } from "@/components/admin/BulkActionsBar";
import CreateJobModal from "@/components/admin/CreateJobModal";
import { Button as UIButton } from "@/components/ui";

const { Title } = Typography;

// Get tag color for job type
function getJobTypeColor(type: string | null): string {
  if (!type) return "default";
  const typeColors: Record<string, string> = {
    "Full-time": "green",
    "Part-time": "blue",
    Internship: "purple",
    Contract: "orange",
    "Co-op": "cyan",
  };
  return typeColors[type] || "default";
}

// Get tag color for work mode
function getWorkModeColor(mode: string | null): string {
  if (!mode) return "default";
  const modeColors: Record<string, string> = {
    Remote: "green",
    "On-site": "blue",
    Hybrid: "purple",
  };
  return modeColors[mode] || "default";
}

// Format date for display
function formatDate(dateString: string | null): string {
  if (!dateString) return "-";
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function AdminJobsListPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [form] = Form.useForm();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<PaginatedResponse<AdminJob> | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [bulkActionLoading, setBulkActionLoading] = useState(false);

  // Get initial values from URL
  const page = parseInt(searchParams.get("page") || "1", 10);
  const search = searchParams.get("search") || "";
  const company = searchParams.get("company") || "";
  const category = searchParams.get("category") || "";
  const isActive = searchParams.get("is_active") || "";

  // Fetch jobs data
  const loadJobs = useCallback(async (params: {
    page?: number;
    search?: string;
    company?: string;
    category?: string;
    isActive?: string;
  } = {}) => {
    setLoading(true);
    const activeValue = params.isActive ?? isActive;
    const result = await fetchJobs({
      page: params.page || page,
      pageSize: 20,
      search: params.search ?? search,
      company: params.company ?? company,
      category: params.category ?? category,
      isActive: activeValue && activeValue !== "all"
        ? activeValue === "true"
        : undefined,
      sortBy: "posted_at",
      sortOrder: "desc",
    });

    if (result.data) {
      setData(result.data);
    } else {
      message.error(result.error || "Failed to load jobs");
    }
    setLoading(false);
  }, [page, search, company, category, isActive]);

  // Initial load
  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  // Set form values from URL on mount
  useEffect(() => {
    form.setFieldsValue({
      search,
      company,
      category,
      is_active: isActive || "all",
    });
  }, [form, search, company, category, isActive]);

  // Handle search form submit
  const handleSearch = (values: {
    search?: string;
    company?: string;
    category?: string;
    is_active?: string;
  }) => {
    const params = new URLSearchParams();
    params.set("page", "1");
    if (values.search) params.set("search", values.search);
    if (values.company) params.set("company", values.company);
    if (values.category) params.set("category", values.category);
    if (values.is_active && values.is_active !== "all") {
      params.set("is_active", values.is_active);
    }
    router.push(`/admin/jobs?${params.toString()}`);
  };

  // Handle reset
  const handleReset = () => {
    form.resetFields();
    router.push("/admin/jobs");
  };

  // Handle table pagination
  const handleTableChange = (pagination: { current?: number }) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(pagination.current || 1));
    router.push(`/admin/jobs?${params.toString()}`);
  };

  // Handle bulk actions
  const handleBulkAction = async (action: "activate" | "deactivate" | "delete") => {
    if (selectedRowKeys.length === 0) return;

    setBulkActionLoading(true);
    const result = await bulkJobAction(selectedRowKeys as string[], action);
    setBulkActionLoading(false);

    if (result.data) {
      message.success(`Successfully ${action}d ${result.data.affected} jobs`);
      setSelectedRowKeys([]);
      loadJobs();
    } else {
      message.error(result.error || `Failed to ${action} jobs`);
    }
  };

  // Handle bulk activate
  const handleBulkActivate = () => handleBulkAction("activate");

  // Handle bulk deactivate
  const handleBulkDeactivate = () => handleBulkAction("deactivate");

  // Handle bulk delete
  const handleBulkDelete = () => handleBulkAction("delete");

  // Clear selection
  const handleClearSelection = () => {
    setSelectedRowKeys([]);
  };

  // Handle job created
  const handleJobCreated = () => {
    loadJobs();
  };

  // Table columns
  const columns = [
    {
      title: "Title",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
      width: 250,
      render: (value: string, record: AdminJob) => (
        <Link
          href={`/admin/jobs/${record.id}`}
          style={{ color: "#1890ff", fontWeight: 500 }}
        >
          {value}
        </Link>
      ),
    },
    {
      title: "Company",
      dataIndex: "company",
      key: "company",
      ellipsis: true,
      width: 150,
    },
    {
      title: "Location",
      dataIndex: "location",
      key: "location",
      ellipsis: true,
      width: 150,
    },
    {
      title: "Category",
      dataIndex: "job_category",
      key: "job_category",
      width: 130,
      render: (value: string | null) =>
        value ? <Tag color="blue">{value}</Tag> : "-",
    },
    {
      title: "Type",
      dataIndex: "job_type",
      key: "job_type",
      width: 110,
      render: (value: string | null) =>
        value ? <Tag color={getJobTypeColor(value)}>{value}</Tag> : "-",
    },
    {
      title: "Work Mode",
      dataIndex: "work_mode",
      key: "work_mode",
      width: 100,
      render: (value: string | null) =>
        value ? <Tag color={getWorkModeColor(value)}>{value}</Tag> : "-",
    },
    {
      title: "Active",
      dataIndex: "is_active",
      key: "is_active",
      width: 80,
      align: "center" as const,
      render: (value: boolean) => (
        <Tag color={value ? "success" : "error"}>
          {value ? "Active" : "Inactive"}
        </Tag>
      ),
    },
    {
      title: "Clicks",
      dataIndex: "click_count",
      key: "click_count",
      width: 80,
      align: "right" as const,
      render: (value: number) => (
        <span style={{ fontWeight: 500 }}>{value.toLocaleString()}</span>
      ),
    },
    {
      title: "Posted At",
      dataIndex: "posted_at",
      key: "posted_at",
      width: 110,
      render: (value: string | null) => formatDate(value),
    },
    {
      title: "Actions",
      key: "actions",
      width: 100,
      fixed: "right" as const,
      render: (_: unknown, record: AdminJob) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => router.push(`/admin/jobs/${record.id}`)}
            title="View job"
          />
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => router.push(`/admin/jobs/${record.id}`)}
            title="Edit job"
          />
        </Space>
      ),
    },
  ];

  // Row selection configuration
  const rowSelection: TableProps<AdminJob>["rowSelection"] = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys);
    },
    selections: [
      Table.SELECTION_ALL,
      Table.SELECTION_INVERT,
      Table.SELECTION_NONE,
    ],
  };

  return (
    <div style={{ paddingBottom: selectedRowKeys.length > 0 ? 80 : 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>
          Jobs
        </Title>
        <UIButton
          variant="primary"
          size="sm"
          onClick={() => setIsCreateModalOpen(true)}
        >
          <Plus className="w-4 h-4" />
          Create Job
        </UIButton>
      </div>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Form
              form={form}
              layout="inline"
              style={{ gap: 16, flexWrap: "wrap" }}
              onFinish={handleSearch}
            >
              <Form.Item name="search" style={{ marginBottom: 0 }}>
                <Input
                  placeholder="Search title/company..."
                  prefix={<SearchOutlined />}
                  allowClear
                  style={{ width: 200 }}
                />
              </Form.Item>

              <Form.Item name="company" style={{ marginBottom: 0 }}>
                <Input
                  placeholder="Filter by company"
                  allowClear
                  style={{ width: 180 }}
                />
              </Form.Item>

              <Form.Item name="category" style={{ marginBottom: 0 }}>
                <Input
                  placeholder="Filter by category"
                  allowClear
                  style={{ width: 160 }}
                />
              </Form.Item>

              <Form.Item name="is_active" style={{ marginBottom: 0 }}>
                <Select
                  placeholder="Active status"
                  allowClear
                  style={{ width: 140 }}
                  options={[
                    { value: "all", label: "All" },
                    { value: "true", label: "Active" },
                    { value: "false", label: "Inactive" },
                  ]}
                />
              </Form.Item>

              <Form.Item style={{ marginBottom: 0 }}>
                <Space>
                  <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>
                    Search
                  </Button>
                  <Button onClick={handleReset} icon={<ReloadOutlined />}>
                    Reset
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        <Col span={24}>
          <Spin spinning={loading}>
            <Table
              dataSource={data?.items || []}
              columns={columns}
              rowKey="id"
              rowSelection={rowSelection}
              scroll={{ x: 1400 }}
              pagination={{
                current: page,
                pageSize: 20,
                total: data?.total || 0,
                pageSizeOptions: ["20", "50", "100"],
                showSizeChanger: false,
                showTotal: (total, range) =>
                  `${range[0]}-${range[1]} of ${total} jobs`,
              }}
              onChange={handleTableChange}
            />
          </Spin>
        </Col>
      </Row>

      {/* Bulk Actions Bar */}
      <BulkActionsBar
        selectedCount={selectedRowKeys.length}
        onActivate={handleBulkActivate}
        onDeactivate={handleBulkDeactivate}
        onDelete={handleBulkDelete}
        onClear={handleClearSelection}
      />

      {/* Create Job Modal */}
      <CreateJobModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleJobCreated}
      />
    </div>
  );
}
