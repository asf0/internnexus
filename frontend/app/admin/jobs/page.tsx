'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Search, RefreshCw, Eye, Edit, Plus } from 'lucide-react';
import Link from 'next/link';
import { Input, Button } from '@/components/ui';
import { SingleSelect } from '@/components/ui/SingleSelect';
import { BulkActionsBar } from '@/components/admin/BulkActionsBar';
import CreateJobModal from '@/components/admin/CreateJobModal';
import {
  fetchJobs,
  bulkJobAction,
  type AdminJob,
  type PaginatedResponse,
} from '@/app/actions/admin';
import { AdminCard, AdminTable, AdminTag, useAdminMessage } from '@/components/admin/ui';
import type { AdminColumn, AdminRowSelection } from '@/components/admin/ui';

function getJobTypeColor(type: string | null): string {
  if (!type) return 'default';
  const typeColors: Record<string, string> = {
    'Full-time': 'green',
    'Part-time': 'blue',
    Internship: 'purple',
    Contract: 'orange',
    'Co-op': 'cyan',
  };
  return typeColors[type] || 'default';
}

function getWorkModeColor(mode: string | null): string {
  if (!mode) return 'default';
  const modeColors: Record<string, string> = {
    Remote: 'green',
    'On-site': 'blue',
    Hybrid: 'purple',
  };
  return modeColors[mode] || 'default';
}

function formatDate(dateString: string | null): string {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

const activeOptions = [
  { value: 'all', label: 'All' },
  { value: 'true', label: 'Active' },
  { value: 'false', label: 'Inactive' },
];

export default function AdminJobsListPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const message = useAdminMessage();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<PaginatedResponse<AdminJob> | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const page = parseInt(searchParams.get('page') || '1', 10);
  const search = searchParams.get('search') || '';
  const company = searchParams.get('company') || '';
  const category = searchParams.get('category') || '';
  const isActive = searchParams.get('is_active') || 'all';

  const [form, setForm] = useState({
    search,
    company,
    category,
    is_active: isActive || 'all',
  });

  useEffect(() => {
    setForm({ search, company, category, is_active: isActive || 'all' });
  }, [search, company, category, isActive]);

  const loadJobs = useCallback(
    async (
      params: {
        page?: number;
        search?: string;
        company?: string;
        category?: string;
        isActive?: string;
      } = {}
    ) => {
      setLoading(true);
      const activeValue = params.isActive ?? isActive;
      const result = await fetchJobs({
        page: params.page || page,
        pageSize: 20,
        search: params.search ?? search,
        company: params.company ?? company,
        category: params.category ?? category,
        isActive: activeValue && activeValue !== 'all' ? activeValue === 'true' : undefined,
        sortBy: 'posted_at',
        sortOrder: 'desc',
      });

      if (result.data) {
        setData(result.data);
      } else {
        message.error(result.error || 'Failed to load jobs');
      }
      setLoading(false);
    },
    [page, search, company, category, isActive, message]
  );

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams();
    params.set('page', '1');
    if (form.search) params.set('search', form.search);
    if (form.company) params.set('company', form.company);
    if (form.category) params.set('category', form.category);
    if (form.is_active && form.is_active !== 'all') {
      params.set('is_active', form.is_active);
    }
    router.push(`/admin/jobs?${params.toString()}`);
  };

  const handleReset = () => {
    setForm({ search: '', company: '', category: '', is_active: 'all' });
    router.push('/admin/jobs');
  };

  const buildPageUrl = useCallback(
    (p: number) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('page', String(p));
      return `/admin/jobs?${params.toString()}`;
    },
    [searchParams]
  );

  const handleBulkAction = async (action: 'activate' | 'deactivate' | 'delete') => {
    if (selectedRowKeys.length === 0) return;

    const result = await bulkJobAction(selectedRowKeys as string[], action);

    if (result.data) {
      message.success(`Successfully ${action}d ${result.data.affected} jobs`);
      setSelectedRowKeys([]);
      loadJobs();
    } else {
      message.error(result.error || `Failed to ${action} jobs`);
    }
  };

  const handleBulkActivate = () => handleBulkAction('activate');
  const handleBulkDeactivate = () => handleBulkAction('deactivate');
  const handleBulkDelete = () => handleBulkAction('delete');
  const handleClearSelection = () => setSelectedRowKeys([]);
  const handleJobCreated = () => loadJobs();

  const columns: AdminColumn<AdminJob>[] = [
    {
      title: 'Title',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      width: 250,
      render: (_value: string, record: AdminJob) => (
        <Link
          href={`/admin/jobs/${record.id}`}
          className="font-medium text-blue-600 hover:underline dark:text-blue-400"
        >
          {record.title}
        </Link>
      ),
    },
    { title: 'Company', dataIndex: 'company', key: 'company', ellipsis: true, width: 150 },
    { title: 'Location', dataIndex: 'location', key: 'location', ellipsis: true, width: 150 },
    {
      title: 'Category',
      dataIndex: 'job_category',
      key: 'job_category',
      width: 130,
      render: (value: string | null) => (value ? <AdminTag color="blue">{value}</AdminTag> : '-'),
    },
    {
      title: 'Type',
      dataIndex: 'job_type',
      key: 'job_type',
      width: 110,
      render: (value: string | null) =>
        value ? <AdminTag color={getJobTypeColor(value)}>{value}</AdminTag> : '-',
    },
    {
      title: 'Work Mode',
      dataIndex: 'work_mode',
      key: 'work_mode',
      width: 100,
      render: (value: string | null) =>
        value ? <AdminTag color={getWorkModeColor(value)}>{value}</AdminTag> : '-',
    },
    {
      title: 'Active',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      align: 'center',
      render: (value: boolean) => (
        <AdminTag color={value ? 'success' : 'error'}>{value ? 'Active' : 'Inactive'}</AdminTag>
      ),
    },
    {
      title: 'Clicks',
      dataIndex: 'click_count',
      key: 'click_count',
      width: 80,
      align: 'right',
      render: (value: number) => <span className="font-medium">{value.toLocaleString()}</span>,
    },
    {
      title: 'Posted At',
      dataIndex: 'posted_at',
      key: 'posted_at',
      width: 110,
      render: (value: string | null) => formatDate(value),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: AdminJob) => (
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/admin/jobs/${record.id}`)}
            title="View job"
            aria-label="View job"
          >
            <Eye className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/admin/jobs/${record.id}`)}
            title="Edit job"
            aria-label="Edit job"
          >
            <Edit className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  const rowSelection: AdminRowSelection = {
    selectedRowKeys,
    onChange: setSelectedRowKeys,
  };

  return (
    <div style={{ paddingBottom: selectedRowKeys.length > 0 ? 80 : 0 }}>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Jobs</h1>
        <Button variant="primary" size="sm" onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="h-4 w-4" />
          Create Job
        </Button>
      </div>

      <AdminCard className="mb-4">
        <form onSubmit={handleSearch} className="flex flex-wrap items-end gap-4">
          <div className="w-52">
            <Input
              placeholder="Search title/company..."
              value={form.search}
              onChange={(e) => setForm((f) => ({ ...f, search: e.target.value }))}
              icon={Search}
            />
          </div>
          <div className="w-48">
            <Input
              placeholder="Filter by company"
              value={form.company}
              onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
            />
          </div>
          <div className="w-40">
            <Input
              placeholder="Filter by category"
              value={form.category}
              onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
            />
          </div>
          <div className="w-40">
            <SingleSelect
              options={activeOptions}
              value={form.is_active}
              onChange={(value) => setForm((f) => ({ ...f, is_active: value }))}
              placeholder="Active status"
            />
          </div>
          <div className="flex items-center gap-2">
            <Button type="submit" variant="primary" size="sm">
              <Search className="h-4 w-4" />
              Search
            </Button>
            <Button type="button" variant="secondary" size="sm" onClick={handleReset}>
              <RefreshCw className="h-4 w-4" />
              Reset
            </Button>
          </div>
        </form>
      </AdminCard>

      <AdminTable
        dataSource={data?.items || []}
        columns={columns}
        rowKey="id"
        rowSelection={rowSelection}
        loading={loading}
        scroll={{ x: 1400 }}
        pagination={
          data
            ? {
                current: page,
                pageSize: 20,
                total: data.total,
                buildPageUrl,
              }
            : false
        }
        emptyText="No jobs found"
      />

      <BulkActionsBar
        selectedCount={selectedRowKeys.length}
        onActivate={handleBulkActivate}
        onDeactivate={handleBulkDeactivate}
        onDelete={handleBulkDelete}
        onClear={handleClearSelection}
      />

      <CreateJobModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleJobCreated}
      />
    </div>
  );
}
