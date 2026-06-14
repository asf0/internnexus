'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { User, History, ShieldAlert } from 'lucide-react';
import { Button, Alert, LoadingSpinner } from '@/components/ui';
import { AdminResult, AdminTabs, useAdminMessage } from '@/components/admin/ui';
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
import {
  UserOverviewTab,
  UserClicksTab,
  UserActionsTab,
  UserActionModals,
} from '@/components/admin/users';
import { type CurrentAdminInfo } from '@/components/admin/users/types';

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

  const refreshUser = async () => {
    const userResult = await fetchUser(userId);
    if (userResult.data) {
      setUser(userResult.data);
      setNotes(userResult.data.notes || '');
    }
  };

  const openModal = (setter: (value: boolean) => void) => {
    setActionError(null);
    setter(true);
  };

  const closeModal = (setter: (value: boolean) => void) => {
    setActionError(null);
    setter(false);
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

  const handleClicksPageChange = (page: number) => {
    setClicksPage(page);
    fetchClicks(page);
  };

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

  const tabItems = [
    {
      key: 'overview',
      label: (
        <span className="flex items-center gap-2">
          <User className="h-4 w-4" />
          Overview
        </span>
      ),
      children: <UserOverviewTab user={user} />,
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
        <UserClicksTab
          clicksData={clicksData}
          clicksLoading={clicksLoading}
          clicksPage={clicksPage}
          pageSize={clicksPageSize}
          onPageChange={handleClicksPageChange}
        />
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
        <UserActionsTab
          user={user}
          currentAdmin={currentAdmin}
          notes={notes}
          isNotesLoading={isNotesLoading}
          isActionLoading={isActionLoading}
          onNotesChange={setNotes}
          onSaveNotes={handleSaveNotes}
          onGrantAdminClick={() => openModal(setShowGrantAdminModal)}
          onRevokeAdminClick={() => openModal(setShowRevokeAdminModal)}
          onDeactivateClick={() => openModal(setShowDeactivateModal)}
          onReactivateClick={() => openModal(setShowReactivateModal)}
          onResetPassword={handleResetPassword}
          onDeleteUser={handleDeleteUser}
        />
      ),
    },
  ];

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

      <UserActionModals
        user={user}
        showGrantAdminModal={showGrantAdminModal}
        showRevokeAdminModal={showRevokeAdminModal}
        showDeactivateModal={showDeactivateModal}
        showReactivateModal={showReactivateModal}
        grantRole={grantRole}
        grantNotes={grantNotes}
        isActionLoading={isActionLoading}
        actionError={actionError}
        onCloseGrantModal={() => closeModal(setShowGrantAdminModal)}
        onCloseRevokeModal={() => closeModal(setShowRevokeAdminModal)}
        onCloseDeactivateModal={() => closeModal(setShowDeactivateModal)}
        onCloseReactivateModal={() => closeModal(setShowReactivateModal)}
        onGrantRoleChange={setGrantRole}
        onGrantNotesChange={setGrantNotes}
        onGrantAdmin={handleGrantAdmin}
        onRevokeAdmin={handleRevokeAdmin}
        onDeactivate={handleDeactivate}
        onReactivate={handleReactivate}
      />
    </>
  );
}
