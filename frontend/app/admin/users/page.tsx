'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Eye, Search, UserPlus, Download, Loader2 } from 'lucide-react';
import { Button, Input, LoadingSpinner, PageHeader } from '@/components/ui';
import { SingleSelect } from '@/components/ui/SingleSelect';
import CreateUserModal from '@/components/admin/CreateUserModal';
import {
  fetchUsers,
  exportUsers,
  type AdminUser,
  type PaginatedResponse,
} from '@/app/actions/admin';
import { AdminTable, AdminTag, useAdminMessage } from '@/components/admin/ui';
import type { AdminColumn } from '@/components/admin/ui';

const adminOptions = [
  { value: 'all', label: 'All' },
  { value: 'true', label: 'Admins' },
  { value: 'false', label: 'Non-admins' },
];

export default function AdminUsersPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const message = useAdminMessage();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<PaginatedResponse<AdminUser> | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const page = Number.parseInt(searchParams.get('page') || '1', 10);
  const search = searchParams.get('search') || '';
  const isAdminFilter = searchParams.get('is_admin') || 'all';

  const [form, setForm] = useState({ search, is_admin: isAdminFilter || 'all' });

  useEffect(() => {
    setForm({ search, is_admin: isAdminFilter || 'all' });
  }, [search, isAdminFilter]);

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
    [page, search, isAdminFilter, message]
  );

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleSearch = (e: React.SyntheticEvent<HTMLFormElement, SubmitEvent>) => {
    e.preventDefault();
    const params = new URLSearchParams();
    params.set('page', '1');
    if (form.search) params.set('search', form.search);
    if (form.is_admin && form.is_admin !== 'all') {
      params.set('is_admin', form.is_admin);
    }
    router.push(`/admin/users?${params.toString()}`);
  };

  const buildPageUrl = useCallback(
    (p: number) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('page', String(p));
      return `/admin/users?${params.toString()}`;
    },
    [searchParams]
  );

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

  const handleUserCreated = () => {
    loadUsers();
  };

  const columns: AdminColumn<AdminUser>[] = [
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      priority: 'primary',
      mobileLabel: 'User',
      ellipsis: true,
      render: (email: string) => <span className="text-foreground font-medium">{email}</span>,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      priority: 'secondary',
      render: (name: string | null) => <span className="text-foreground-muted">{name || '-'}</span>,
    },
    {
      title: 'Admin Role',
      dataIndex: 'admin_role',
      key: 'admin_role',
      width: 120,
      priority: 'secondary',
      render: (role: string | null) => {
        if (!role) return null;
        const color = role === 'super_admin' ? 'gold' : 'blue';
        return <AdminTag color={color}>{role}</AdminTag>;
      },
    },
    {
      title: 'Provider',
      dataIndex: 'provider',
      key: 'provider',
      width: 100,
      priority: 'detail',
      render: (provider: string | null) => {
        if (!provider) {
          return <AdminTag color="default">credentials</AdminTag>;
        }
        const providerColors: Record<string, string> = {
          github: 'default',
          google: 'blue',
        };
        return <AdminTag color={providerColors[provider] || 'default'}>{provider}</AdminTag>;
      },
    },
    {
      title: 'Active',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      priority: 'secondary',
      render: (active: boolean) => (
        <AdminTag color={active ? 'green' : 'red'}>{active ? 'Active' : 'Inactive'}</AdminTag>
      ),
    },
    {
      title: 'Has Password',
      dataIndex: 'has_password',
      key: 'has_password',
      width: 110,
      priority: 'detail',
      render: (hasPassword: boolean) => (
        <AdminTag color={hasPassword ? 'green' : 'default'}>{hasPassword ? 'Yes' : 'No'}</AdminTag>
      ),
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      priority: 'detail',
      render: (date: string) =>
        new Date(date).toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
        }),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 80,
      priority: 'secondary',
      render: (_: unknown, record: AdminUser) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push(`/admin/users/${record.id}`)}
          title="View user details"
          aria-label="View user details"
        >
          <Eye className="h-4 w-4" />
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Users"
        className="mb-6"
        actions={
          <>
            <Button variant="outline" size="sm" onClick={handleExport} disabled={isExporting}>
              {isExporting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              {isExporting ? 'Exporting...' : 'Export CSV'}
            </Button>
            <Button variant="primary" size="sm" onClick={() => setIsCreateModalOpen(true)}>
              <UserPlus className="h-4 w-4" />
              Create User
            </Button>
          </>
        }
      />

      <form
        onSubmit={handleSearch}
        className="mb-4 grid grid-cols-1 items-end gap-4 sm:grid-cols-[minmax(0,18rem)_10rem_auto]"
      >
        <div className="min-w-0">
          <Input
            placeholder="Search by email or name..."
            value={form.search}
            onChange={(e) => setForm((f) => ({ ...f, search: e.target.value }))}
            icon={Search}
          />
        </div>
        <div className="min-w-0">
          <SingleSelect
            options={adminOptions}
            value={form.is_admin}
            onChange={(value) => setForm((f) => ({ ...f, is_admin: value }))}
            placeholder="Admin Filter"
          />
        </div>
        <Button type="submit" variant="primary" size="sm">
          Search
        </Button>
      </form>

      {loading && !data ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner />
        </div>
      ) : (
        <AdminTable
          dataSource={data?.items || []}
          columns={columns}
          rowKey="id"
          loading={loading}
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
          size="small"
          emptyText="No users found"
        />
      )}

      <CreateUserModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleUserCreated}
      />
    </div>
  );
}
