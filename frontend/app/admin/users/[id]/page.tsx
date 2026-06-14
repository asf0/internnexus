'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Mail,
  User,
  Shield,
  Key,
  Calendar,
  CheckCircle,
  ShieldAlert,
  UserCog,
  Ban,
  RotateCcw,
  Loader2,
  History,
  FileText,
  KeyRound,
  Trash2,
} from 'lucide-react';
import { Button, Badge, Alert, IconContainer, Input, LoadingSpinner } from '@/components/ui';
import { SingleSelect } from '@/components/ui/SingleSelect';
import { Modal } from '@/components/modals';
import {
  AdminCard,
  AdminPopconfirm,
  AdminResult,
  AdminTable,
  AdminTabs,
  AdminTag,
  useAdminMessage,
} from '@/components/admin/ui';
import type { AdminColumn } from '@/components/admin/ui';
import {
  fetchUser,
  fetchCurrentAdmin,
  grantAdmin,
  revokeAdmin,
  deactivateUser,
  reactivateUser,
  getUserClicks,
  updateUserNotes,
  resetUserPassword,
  deleteUser,
  type AdminUser,
  type UserClick,
  type PaginatedResponse,
} from '@/app/actions/admin';

interface CurrentAdminInfo {
  id: string;
  role: 'admin' | 'super_admin';
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getAdminRoleBadgeVariant(role: string): 'purple' | 'danger' {
  return role === 'super_admin' ? 'danger' : 'purple';
}

export default function AdminUserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.id as string;
  const message = useAdminMessage();

  const [user, setUser] = useState<AdminUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [currentAdmin, setCurrentAdmin] = useState<CurrentAdminInfo | null>(null);
  const [activeTab, setActiveTab] = useState('overview');

  const [showGrantAdminModal, setShowGrantAdminModal] = useState(false);
  const [showRevokeAdminModal, setShowRevokeAdminModal] = useState(false);
  const [showDeactivateModal, setShowDeactivateModal] = useState(false);
  const [showReactivateModal, setShowReactivateModal] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const [grantRole, setGrantRole] = useState('admin');
  const [grantNotes, setGrantNotes] = useState('');

  const [notes, setNotes] = useState('');
  const [isNotesLoading, setIsNotesLoading] = useState(false);

  const [clicksData, setClicksData] = useState<PaginatedResponse<UserClick> | null>(null);
  const [clicksLoading, setClicksLoading] = useState(false);
  const [clicksPage, setClicksPage] = useState(1);
  const clicksPageSize = 10;

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);

      const userResult = await fetchUser(userId);
      if (userResult.data) {
        setUser(userResult.data);
        setNotes(userResult.data.notes || '');
      } else {
        setIsError(true);
      }

      const adminResult = await fetchCurrentAdmin();
      if (adminResult.data) {
        setCurrentAdmin(adminResult.data);
      }

      setIsLoading(false);
    }
    loadData();
  }, [userId]);

  const fetchClicks = useCallback(
    async (page: number) => {
      setClicksLoading(true);
      const result = await getUserClicks(userId, page, clicksPageSize);
      if (result.data) {
        setClicksData(result.data);
      }
      setClicksLoading(false);
    },
    [userId]
  );

  useEffect(() => {
    if (activeTab === 'clicks' && !clicksData) {
      fetchClicks(1);
    }
  }, [activeTab, clicksData, fetchClicks]);

  const isSuperAdmin = currentAdmin?.role === 'super_admin';
  const isOwnProfile = currentAdmin?.id === userId;

  const refreshUser = async () => {
    const userResult = await fetchUser(userId);
    if (userResult.data) {
      setUser(userResult.data);
      setNotes(userResult.data.notes || '');
    }
  };

  const handleGrantAdmin = async () => {
    setIsActionLoading(true);
    setActionError(null);

    const result = await grantAdmin(
      userId,
      grantRole as 'admin' | 'super_admin',
      grantNotes || undefined
    );

    if (result.data || ('success' in result && result.success)) {
      setShowGrantAdminModal(false);
      setGrantRole('admin');
      setGrantNotes('');
      message.success('Admin access granted successfully');
      await refreshUser();
    } else {
      setActionError(result.error || 'An error occurred');
    }

    setIsActionLoading(false);
  };

  const handleRevokeAdmin = async () => {
    setIsActionLoading(true);
    setActionError(null);

    const result = await revokeAdmin(userId);

    if ('success' in result && result.success) {
      setShowRevokeAdminModal(false);
      message.success('Admin access revoked successfully');
      await refreshUser();
    } else {
      setActionError(result.error || 'An error occurred');
    }

    setIsActionLoading(false);
  };

  const handleDeactivate = async () => {
    setIsActionLoading(true);
    setActionError(null);

    const result = await deactivateUser(userId);

    if ('success' in result && result.success) {
      setShowDeactivateModal(false);
      message.success('User deactivated successfully');
      await refreshUser();
    } else {
      setActionError(result.error || 'An error occurred');
    }

    setIsActionLoading(false);
  };

  const handleReactivate = async () => {
    setIsActionLoading(true);
    setActionError(null);

    const result = await reactivateUser(userId);

    if ('success' in result && result.success) {
      setShowReactivateModal(false);
      message.success('User reactivated successfully');
      await refreshUser();
    } else {
      setActionError(result.error || 'An error occurred');
    }

    setIsActionLoading(false);
  };

  const handleSaveNotes = async () => {
    setIsNotesLoading(true);
    const result = await updateUserNotes(userId, notes || null);
    if (result.success) {
      message.success('Notes saved successfully');
      await refreshUser();
    } else {
      message.error(result.error || 'Failed to save notes');
    }
    setIsNotesLoading(false);
  };

  const handleResetPassword = async () => {
    setIsActionLoading(true);
    const result = await resetUserPassword(userId);
    if (result.success) {
      message.success(result.message || 'Password reset request completed');
    } else {
      message.error(result.error || 'Password reset email delivery is not configured');
    }
    setIsActionLoading(false);
  };

  const handleDeleteUser = async () => {
    setIsActionLoading(true);
    const result = await deleteUser(userId);
    if (result.success) {
      message.success('User deleted successfully');
      router.push('/admin/users');
    } else {
      message.error(result.error || 'Failed to delete user');
    }
    setIsActionLoading(false);
  };

  const clickColumns: AdminColumn<UserClick>[] = [
    { title: 'Job Title', dataIndex: 'job_title', key: 'job_title', ellipsis: true },
    { title: 'Company', dataIndex: 'company', key: 'company', ellipsis: true },
    {
      title: 'Clicked At',
      dataIndex: 'clicked_at',
      key: 'clicked_at',
      width: 180,
      render: (date: string) => formatDate(date),
    },
  ];

  const tabItems = [
    {
      key: 'overview',
      label: (
        <span className="flex items-center gap-2">
          <User className="h-4 w-4" />
          Overview
        </span>
      ),
      children: (
        <AdminCard className="shadow-sm">
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
              <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
                <Mail className="h-4 w-4" />
                Email
              </dt>
              <dd className="dark:text-md-on-surface text-slate-900">{user?.email}</dd>
            </div>
            <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
              <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
                <User className="h-4 w-4" />
                Name
              </dt>
              <dd className="dark:text-md-on-surface text-slate-900">
                {user?.name || <span className="text-slate-400">Not set</span>}
              </dd>
            </div>
            <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
              <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
                <Shield className="h-4 w-4" />
                Admin Role
              </dt>
              <dd className="dark:text-md-on-surface text-slate-900">
                {user?.admin_role ? (
                  <Badge variant={getAdminRoleBadgeVariant(user.admin_role)}>
                    {user.admin_role === 'super_admin' ? 'Super Admin' : 'Admin'}
                  </Badge>
                ) : (
                  <span className="text-slate-400">Not an admin</span>
                )}
              </dd>
            </div>
            <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
              <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
                <Key className="h-4 w-4" />
                Provider
              </dt>
              <dd className="dark:text-md-on-surface text-slate-900 capitalize">
                {user?.provider || 'credentials'}
              </dd>
            </div>
            <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
              <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
                <CheckCircle className="h-4 w-4" />
                Active Status
              </dt>
              <dd className="dark:text-md-on-surface text-slate-900">
                {user?.is_active ? (
                  <Badge variant="success">Active</Badge>
                ) : (
                  <Badge variant="danger">Deactivated</Badge>
                )}
              </dd>
            </div>
            <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
              <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
                <Key className="h-4 w-4" />
                Has Password
              </dt>
              <dd className="dark:text-md-on-surface text-slate-900">
                {user?.has_password ? (
                  <AdminTag color="green">Yes</AdminTag>
                ) : (
                  <AdminTag color="default">No</AdminTag>
                )}
              </dd>
            </div>
            <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
              <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
                <Calendar className="h-4 w-4" />
                Created At
              </dt>
              <dd className="dark:text-md-on-surface text-slate-900">
                {user?.created_at && formatDate(user.created_at)}
              </dd>
            </div>
          </dl>
        </AdminCard>
      ),
    },
    {
      key: 'clicks',
      label: (
        <span className="flex items-center gap-2">
          <History className="h-4 w-4" />
          Click History
        </span>
      ),
      children: (
        <AdminCard className="shadow-sm">
          <AdminTable
            columns={clickColumns}
            dataSource={clicksData?.items || []}
            rowKey="id"
            loading={clicksLoading}
            pagination={
              clicksData
                ? {
                    current: clicksPage,
                    pageSize: clicksPageSize,
                    total: clicksData.total,
                    onChange: (page) => {
                      setClicksPage(page);
                      fetchClicks(page);
                    },
                  }
                : false
            }
            emptyText="No click history found for this user"
          />
        </AdminCard>
      ),
    },
    {
      key: 'actions',
      label: (
        <span className="flex items-center gap-2">
          <ShieldAlert className="h-4 w-4" />
          Admin Actions
        </span>
      ),
      children: (
        <div className="space-y-6">
          <AdminCard
            title={
              <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
                <FileText className="h-5 w-5" />
                Admin Notes
              </span>
            }
            className="shadow-sm"
          >
            <div className="space-y-4">
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add notes about this user..."
                className="min-h-[120px] w-full resize-y rounded-lg border border-slate-200 bg-white p-3 text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
              />
              <div className="flex justify-end">
                <Button variant="primary" onClick={handleSaveNotes} disabled={isNotesLoading}>
                  {isNotesLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save Notes'}
                </Button>
              </div>
            </div>
          </AdminCard>

          {isSuperAdmin && !isOwnProfile && (
            <AdminCard
              title={
                <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
                  <ShieldAlert className="h-5 w-5" />
                  User Actions
                </span>
              }
              className="shadow-sm"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-lg bg-slate-50 p-4 dark:bg-slate-800/50">
                  <div>
                    <h4 className="font-medium text-slate-900 dark:text-slate-100">Admin Access</h4>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      {user?.admin_role
                        ? `User has ${user.admin_role === 'super_admin' ? 'super admin' : 'admin'} privileges`
                        : 'User does not have admin access'}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {!user?.admin_role && (
                      <Button variant="primary" onClick={() => setShowGrantAdminModal(true)}>
                        <UserCog className="h-4 w-4" />
                        Grant Admin
                      </Button>
                    )}
                    {user?.admin_role && (
                      <Button
                        variant="outline"
                        onClick={() => setShowRevokeAdminModal(true)}
                        className="border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                      >
                        <ShieldAlert className="h-4 w-4" />
                        Revoke Admin
                      </Button>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between rounded-lg bg-slate-50 p-4 dark:bg-slate-800/50">
                  <div>
                    <h4 className="font-medium text-slate-900 dark:text-slate-100">
                      Account Status
                    </h4>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      {user?.is_active
                        ? 'User account is currently active'
                        : 'User account has been deactivated'}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {user?.is_active && (
                      <Button
                        variant="outline"
                        onClick={() => setShowDeactivateModal(true)}
                        className="border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                      >
                        <Ban className="h-4 w-4" />
                        Deactivate
                      </Button>
                    )}
                    {!user?.is_active && (
                      <Button variant="primary" onClick={() => setShowReactivateModal(true)}>
                        <RotateCcw className="h-4 w-4" />
                        Reactivate
                      </Button>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between rounded-lg bg-slate-50 p-4 dark:bg-slate-800/50">
                  <div>
                    <h4 className="font-medium text-slate-900 dark:text-slate-100">Password</h4>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      Password reset email delivery is not configured yet
                    </p>
                  </div>
                  <AdminPopconfirm
                    title="Reset Password"
                    description="Record a password reset request for this user?"
                    onConfirm={handleResetPassword}
                    okText="Record request"
                    cancelText="Cancel"
                    okButtonProps={{ loading: isActionLoading }}
                  >
                    <Button variant="outline">
                      <KeyRound className="h-4 w-4" />
                      Reset Password
                    </Button>
                  </AdminPopconfirm>
                </div>

                <div className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
                  <div>
                    <h4 className="font-medium text-red-900 dark:text-red-100">Danger Zone</h4>
                    <p className="text-sm text-red-700 dark:text-red-300">
                      Permanently delete this user and all associated data
                    </p>
                  </div>
                  <AdminPopconfirm
                    title="Delete User"
                    description={
                      <div>
                        <p className="font-medium text-red-600">This action cannot be undone!</p>
                        <p>All user data will be permanently deleted.</p>
                      </div>
                    }
                    onConfirm={handleDeleteUser}
                    okText="Yes, delete user"
                    cancelText="Cancel"
                    okButtonProps={{ loading: isActionLoading, danger: true }}
                  >
                    <Button
                      variant="outline"
                      className="border-red-300 text-red-600 hover:bg-red-100 dark:hover:bg-red-900/40"
                    >
                      <Trash2 className="h-4 w-4" />
                      Delete User
                    </Button>
                  </AdminPopconfirm>
                </div>
              </div>
            </AdminCard>
          )}

          {isOwnProfile && (
            <Alert type="info">
              You cannot modify your own admin status or account activation.
            </Alert>
          )}
        </div>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <LoadingSpinner size="lg" />
        <span className="sr-only">Loading user details...</span>
      </div>
    );
  }

  if (isError || !user) {
    return (
      <AdminResult
        status="404"
        title="User Not Found"
        subTitle="The requested user could not be found."
        extra={
          <Button variant="primary" onClick={() => router.push('/admin/users')}>
            Back to Users
          </Button>
        }
      />
    );
  }

  return (
    <>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              User: {user.name || user.email}
            </h1>
          </div>
          <Button variant="secondary" onClick={() => router.push('/admin/users')}>
            Back to Users
          </Button>
        </div>

        {actionError && (
          <Alert type="error" className="mb-4">
            {actionError}
          </Alert>
        )}

        <AdminTabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </div>

      {/* Grant Admin Modal */}
      <Modal
        isOpen={showGrantAdminModal}
        onClose={() => {
          setShowGrantAdminModal(false);
          setGrantRole('admin');
          setGrantNotes('');
          setActionError(null);
        }}
        title={
          <div className="flex items-center gap-3">
            <IconContainer icon={UserCog} color="purple" />
            <span>Grant Admin Access</span>
          </div>
        }
        size="md"
      >
        <div className="space-y-4">
          <p className="text-slate-600 dark:text-slate-400">
            Grant admin privileges to <strong>{user.email}</strong>
          </p>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Admin Role
            </label>
            <SingleSelect
              options={[
                { value: 'admin', label: 'Admin' },
                { value: 'super_admin', label: 'Super Admin' },
              ]}
              value={grantRole}
              onChange={setGrantRole}
              placeholder="Select role"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Notes (optional)
            </label>
            <Input
              type="text"
              value={grantNotes}
              onChange={(e) => setGrantNotes(e.target.value)}
              placeholder="Reason for granting admin access..."
            />
          </div>

          <div className="flex gap-3 pt-4">
            <Button
              variant="secondary"
              onClick={() => setShowGrantAdminModal(false)}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleGrantAdmin}
              disabled={isActionLoading}
              className="flex-1"
            >
              {isActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Grant Access'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Revoke Admin Modal */}
      <Modal
        isOpen={showRevokeAdminModal}
        onClose={() => {
          setShowRevokeAdminModal(false);
          setActionError(null);
        }}
        title={
          <div className="flex items-center gap-3">
            <IconContainer icon={ShieldAlert} color="red" />
            <span>Revoke Admin Access</span>
          </div>
        }
        size="md"
      >
        <div className="space-y-4">
          <p className="text-slate-600 dark:text-slate-400">
            Are you sure you want to revoke admin access from <strong>{user.email}</strong>?
          </p>

          <Alert type="warning">
            This action will remove all admin privileges from this user. They will no longer be able
            to access the admin panel.
          </Alert>

          <div className="flex gap-3 pt-4">
            <Button
              variant="secondary"
              onClick={() => setShowRevokeAdminModal(false)}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleRevokeAdmin}
              disabled={isActionLoading}
              className="flex-1 bg-red-600 hover:bg-red-700"
            >
              {isActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Revoke Access'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Deactivate User Modal */}
      <Modal
        isOpen={showDeactivateModal}
        onClose={() => {
          setShowDeactivateModal(false);
          setActionError(null);
        }}
        title={
          <div className="flex items-center gap-3">
            <IconContainer icon={Ban} color="red" />
            <span>Deactivate User</span>
          </div>
        }
        size="md"
      >
        <div className="space-y-4">
          <p className="text-slate-600 dark:text-slate-400">
            Are you sure you want to deactivate <strong>{user.email}</strong>?
          </p>

          <Alert type="warning">
            This will prevent the user from logging in and accessing their account. The user can be
            reactivated later.
          </Alert>

          <div className="flex gap-3 pt-4">
            <Button
              variant="secondary"
              onClick={() => setShowDeactivateModal(false)}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleDeactivate}
              disabled={isActionLoading}
              className="flex-1 bg-red-600 hover:bg-red-700"
            >
              {isActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Deactivate'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Reactivate User Modal */}
      <Modal
        isOpen={showReactivateModal}
        onClose={() => {
          setShowReactivateModal(false);
          setActionError(null);
        }}
        title={
          <div className="flex items-center gap-3">
            <IconContainer icon={RotateCcw} color="green" />
            <span>Reactivate User</span>
          </div>
        }
        size="md"
      >
        <div className="space-y-4">
          <p className="text-slate-600 dark:text-slate-400">
            Are you sure you want to reactivate <strong>{user.email}</strong>?
          </p>

          <Alert type="info">
            This will restore the user&apos;s access to their account. They will be able to log in
            again.
          </Alert>

          <div className="flex gap-3 pt-4">
            <Button
              variant="secondary"
              onClick={() => setShowReactivateModal(false)}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleReactivate}
              disabled={isActionLoading}
              className="flex-1"
            >
              {isActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Reactivate'}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
