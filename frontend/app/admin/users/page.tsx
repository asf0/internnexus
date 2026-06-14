'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Table, Form, Input, Select, Button, Tag, Typography, Spin, message } from 'antd';
import { EyeOutlined, SearchOutlined } from '@ant-design/icons';
import { UserPlus, Download } from 'lucide-react';
import { Button as UIButton } from '@/components/ui';
import CreateUserModal from '@/components/admin/CreateUserModal';
import {
  fetchUsers,
  exportUsers,
  type AdminUser,
  type PaginatedResponse,
} from '@/app/actions/admin';

const { Title } = Typography;

export default function AdminUsersPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [form] = Form.useForm();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<PaginatedResponse<AdminUser> | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Get initial values from URL
  const page = parseInt(searchParams.get('page') || '1', 10);
  const search = searchParams.get('search') || '';
  const isAdmin = searchParams.get('is_admin') || '';

  // Fetch users data
  const loadUsers = useCallback(
    async (
      params: {
        page?: number;
        search?: string;
        isAdmin?: string;
      } = {}
    ) => {
      setLoading(true);
      const result = await fetchUsers({
        page: params.page || page,
        pageSize: 20,
        search: params.search ?? search,
        isAdmin: params.isAdmin && params.isAdmin !== 'all' ? params.isAdmin === 'true' : undefined,
        sortBy: 'created_at',
        sortOrder: 'desc',
      });

      if (result.data) {
        setData(result.data);
      } else {
        message.error(result.error || 'Failed to load users');
      }
      setLoading(false);
    },
    [page, search, isAdmin]
  );

  // Initial load
  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // Set form values from URL on mount
  useEffect(() => {
    form.setFieldsValue({
      search,
      is_admin: isAdmin || undefined,
    });
  }, [form, search, isAdmin]);

  // Handle search form submit
  const handleSearch = (values: { search?: string; is_admin?: string }) => {
    const params = new URLSearchParams();
    params.set('page', '1');
    if (values.search) params.set('search', values.search);
    if (values.is_admin) params.set('is_admin', values.is_admin);
    router.push(`/admin/users?${params.toString()}`);
  };

  // Handle table pagination
  const handleTableChange = (pagination: { current?: number }) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('page', String(pagination.current || 1));
    router.push(`/admin/users?${params.toString()}`);
  };

  // Handle CSV export
  const handleExport = async () => {
    setIsExporting(true);
    const result = await exportUsers();
    if (result.data) {
      const blob = new Blob([result.data], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'users.csv';
      a.click();
      URL.revokeObjectURL(url);
    } else {
      message.error(result.error || 'Failed to export users');
    }
    setIsExporting(false);
  };

  // Handle successful user creation
  const handleUserCreated = () => {
    loadUsers();
  };

  const columns = [
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      ellipsis: true,
      render: (email: string) => (
        <span className="font-medium text-slate-900 dark:text-slate-100">{email}</span>
      ),
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (name: string | null) => (
        <span className="text-slate-600 dark:text-slate-400">{name || '-'}</span>
      ),
    },
    {
      title: 'Admin Role',
      dataIndex: 'admin_role',
      key: 'admin_role',
      width: 120,
      render: (role: string | null) => {
        if (!role) return null;
        const color = role === 'super_admin' ? 'gold' : 'blue';
        return <Tag color={color}>{role}</Tag>;
      },
    },
    {
      title: 'Provider',
      dataIndex: 'provider',
      key: 'provider',
      width: 100,
      render: (provider: string | null) => {
        if (!provider) {
          return <Tag color="default">credentials</Tag>;
        }
        const providerColors: Record<string, string> = {
          github: 'default',
          google: 'blue',
        };
        return <Tag color={providerColors[provider] || 'default'}>{provider}</Tag>;
      },
    },
    {
      title: 'Active',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>{active ? 'Active' : 'Inactive'}</Tag>
      ),
    },
    {
      title: 'Has Password',
      dataIndex: 'has_password',
      key: 'has_password',
      width: 110,
      render: (hasPassword: boolean) => (
        <Tag color={hasPassword ? 'green' : 'default'}>{hasPassword ? 'Yes' : 'No'}</Tag>
      ),
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date: string) => {
        return new Date(date).toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
        });
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: AdminUser) => (
        <Button
          type="text"
          icon={<EyeOutlined />}
          onClick={() => router.push(`/admin/users/${record.id}`)}
          title="View user details"
        />
      ),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <Title level={3} style={{ marginBottom: 0 }}>
          Users
        </Title>
        <div className="flex items-center gap-2">
          <UIButton variant="outline" size="sm" onClick={handleExport} disabled={isExporting}>
            <Download className="h-4 w-4" />
            {isExporting ? 'Exporting...' : 'Export CSV'}
          </UIButton>
          <UIButton variant="primary" size="sm" onClick={() => setIsCreateModalOpen(true)}>
            <UserPlus className="h-4 w-4" />
            Create User
          </UIButton>
        </div>
      </div>

      <Form form={form} layout="inline" style={{ marginBottom: 16 }} onFinish={handleSearch}>
        <Form.Item name="search">
          <Input.Search
            placeholder="Search by email or name..."
            allowClear
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
          />
        </Form.Item>
        <Form.Item name="is_admin">
          <Select
            style={{ width: 150 }}
            placeholder="Admin Filter"
            allowClear
            options={[
              { label: 'All', value: 'all' },
              { label: 'Admins', value: 'true' },
              { label: 'Non-admins', value: 'false' },
            ]}
          />
        </Form.Item>
        <Button type="primary" htmlType="submit">
          Search
        </Button>
      </Form>

      <Spin spinning={loading}>
        <Table
          dataSource={data?.items || []}
          columns={columns}
          rowKey="id"
          pagination={{
            current: page,
            pageSize: 20,
            total: data?.total || 0,
            pageSizeOptions: ['20', '50', '100'],
            showSizeChanger: false,
            showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} users`,
          }}
          scroll={{ x: 1000 }}
          size="small"
          onChange={handleTableChange}
        />
      </Spin>

      <CreateUserModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleUserCreated}
      />
    </div>
  );
}
