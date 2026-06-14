"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, Descriptions, Tag, Spin, Result, Typography, Tabs, Table, Popconfirm, message } from "antd";
import type { TabsProps } from "antd";
import type { ColumnsType } from "antd/es/table";
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
} from "lucide-react";
import { Button, Badge, Alert, IconContainer } from "@/components/ui";
import { Modal } from "@/components/modals";
import { SingleSelect } from "@/components/ui/SingleSelect";
import { Input } from "@/components/ui/Input";
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
} from "@/app/actions/admin";

const { Title } = Typography;

// Types
interface CurrentAdminInfo {
  id: string;
  role: "admin" | "super_admin";
}

// Format date for display
function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Admin role badge color
function getAdminRoleBadgeVariant(role: string): "purple" | "danger" {
  return role === "super_admin" ? "danger" : "purple";
}

export default function AdminUserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.id as string;

  // State for data
  const [user, setUser] = useState<AdminUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [currentAdmin, setCurrentAdmin] = useState<CurrentAdminInfo | null>(null);

  // State for tabs
  const [activeTab, setActiveTab] = useState("overview");

  // State for modals and actions
  const [showGrantAdminModal, setShowGrantAdminModal] = useState(false);
  const [showRevokeAdminModal, setShowRevokeAdminModal] = useState(false);
  const [showDeactivateModal, setShowDeactivateModal] = useState(false);
  const [showReactivateModal, setShowReactivateModal] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Grant admin form state
  const [grantRole, setGrantRole] = useState("admin");
  const [grantNotes, setGrantNotes] = useState("");

  // Notes state
  const [notes, setNotes] = useState("");
  const [isNotesLoading, setIsNotesLoading] = useState(false);

  // Click history state
  const [clicksData, setClicksData] = useState<PaginatedResponse<UserClick> | null>(null);
  const [clicksLoading, setClicksLoading] = useState(false);
  const [clicksPage, setClicksPage] = useState(1);
  const clicksPageSize = 10;

  // Fetch user data
  useEffect(() => {
    async function loadData() {
      setIsLoading(true);

      // Fetch user data
      const userResult = await fetchUser(userId);
      if (userResult.data) {
        setUser(userResult.data);
        setNotes(userResult.data.notes || "");
      } else {
        setIsError(true);
      }

      // Fetch current admin info
      const adminResult = await fetchCurrentAdmin();
      if (adminResult.data) {
        setCurrentAdmin(adminResult.data);
      }

      setIsLoading(false);
    }
    loadData();
  }, [userId]);

  // Fetch clicks when tab changes to click history
  const fetchClicks = useCallback(async (page: number) => {
    setClicksLoading(true);
    const result = await getUserClicks(userId, page, clicksPageSize);
    if (result.data) {
      setClicksData(result.data);
    }
    setClicksLoading(false);
  }, [userId]);

  // Load clicks when tab changes
  useEffect(() => {
    if (activeTab === "clicks" && !clicksData) {
      fetchClicks(1);
    }
  }, [activeTab, clicksData, fetchClicks]);

  const isSuperAdmin = currentAdmin?.role === "super_admin";
  const isOwnProfile = currentAdmin?.id === userId;

  // Admin action handlers
  const handleGrantAdmin = async () => {
    setIsActionLoading(true);
    setActionError(null);

    const result = await grantAdmin(
      userId,
      grantRole as "admin" | "super_admin",
      grantNotes || undefined
    );

    if (result.data || ("success" in result && result.success)) {
      setShowGrantAdminModal(false);
      setGrantRole("admin");
      setGrantNotes("");
      message.success("Admin access granted successfully");
      // Refetch user data
      const userResult = await fetchUser(userId);
      if (userResult.data) {
        setUser(userResult.data);
      }
    } else {
      setActionError(result.error || "An error occurred");
    }

    setIsActionLoading(false);
  };

  const handleRevokeAdmin = async () => {
    setIsActionLoading(true);
    setActionError(null);

    const result = await revokeAdmin(userId);

    if (("success" in result && result.success)) {
      setShowRevokeAdminModal(false);
      message.success("Admin access revoked successfully");
      // Refetch user data
      const userResult = await fetchUser(userId);
      if (userResult.data) {
        setUser(userResult.data);
      }
    } else {
      setActionError(result.error || "An error occurred");
    }

    setIsActionLoading(false);
  };

  const handleDeactivate = async () => {
    setIsActionLoading(true);
    setActionError(null);

    const result = await deactivateUser(userId);

    if (("success" in result && result.success)) {
      setShowDeactivateModal(false);
      message.success("User deactivated successfully");
      // Refetch user data
      const userResult = await fetchUser(userId);
      if (userResult.data) {
        setUser(userResult.data);
      }
    } else {
      setActionError(result.error || "An error occurred");
    }

    setIsActionLoading(false);
  };

  const handleReactivate = async () => {
    setIsActionLoading(true);
    setActionError(null);

    const result = await reactivateUser(userId);

    if (("success" in result && result.success)) {
      setShowReactivateModal(false);
      message.success("User reactivated successfully");
      // Refetch user data
      const userResult = await fetchUser(userId);
      if (userResult.data) {
        setUser(userResult.data);
      }
    } else {
      setActionError(result.error || "An error occurred");
    }

    setIsActionLoading(false);
  };

  // Notes handler
  const handleSaveNotes = async () => {
    setIsNotesLoading(true);
    const result = await updateUserNotes(userId, notes || null);
    if (result.success) {
      message.success("Notes saved successfully");
      const userResult = await fetchUser(userId);
      if (userResult.data) {
        setUser(userResult.data);
      }
    } else {
      message.error(result.error || "Failed to save notes");
    }
    setIsNotesLoading(false);
  };

  // Reset password handler
  const handleResetPassword = async () => {
    setIsActionLoading(true);
    const result = await resetUserPassword(userId);
    if (result.success) {
      message.success(result.message || "Password reset request completed");
    } else {
      message.error(result.error || "Password reset email delivery is not configured");
    }
    setIsActionLoading(false);
  };

  // Delete user handler
  const handleDeleteUser = async () => {
    setIsActionLoading(true);
    const result = await deleteUser(userId);
    if (result.success) {
      message.success("User deleted successfully");
      router.push("/admin/users");
    } else {
      message.error(result.error || "Failed to delete user");
    }
    setIsActionLoading(false);
  };

  // Click history table columns
  const clickColumns: ColumnsType<UserClick> = [
    {
      title: "Job Title",
      dataIndex: "job_title",
      key: "job_title",
      ellipsis: true,
    },
    {
      title: "Company",
      dataIndex: "company",
      key: "company",
      ellipsis: true,
    },
    {
      title: "Clicked At",
      dataIndex: "clicked_at",
      key: "clicked_at",
      width: 180,
      render: (date: string) => formatDate(date),
    },
  ];

  // Tab items
  const tabItems: TabsProps["items"] = [
    {
      key: "overview",
      label: (
        <span className="flex items-center gap-2">
          <User className="w-4 h-4" />
          Overview
        </span>
      ),
      children: (
        <Card className="shadow-sm">
          <Descriptions column={{ xs: 1, sm: 2, md: 2, lg: 2 }} bordered size="small">
            <Descriptions.Item
              label={
                <span className="flex items-center gap-2">
                  <Mail className="w-4 h-4" />
                  Email
                </span>
              }
            >
              <span className="text-slate-900 dark:text-slate-100">{user?.email}</span>
            </Descriptions.Item>

            <Descriptions.Item
              label={
                <span className="flex items-center gap-2">
                  <User className="w-4 h-4" />
                  Name
                </span>
              }
            >
              <span className="text-slate-900 dark:text-slate-100">
                {user?.name || <span className="text-slate-400">Not set</span>}
              </span>
            </Descriptions.Item>

            <Descriptions.Item
              label={
                <span className="flex items-center gap-2">
                  <Shield className="w-4 h-4" />
                  Admin Role
                </span>
              }
            >
              {user?.admin_role ? (
                <Badge variant={getAdminRoleBadgeVariant(user.admin_role)}>
                  {user.admin_role === "super_admin" ? "Super Admin" : "Admin"}
                </Badge>
              ) : (
                <span className="text-slate-400">Not an admin</span>
              )}
            </Descriptions.Item>

            <Descriptions.Item
              label={
                <span className="flex items-center gap-2">
                  <Key className="w-4 h-4" />
                  Provider
                </span>
              }
            >
              <span className="text-slate-900 dark:text-slate-100 capitalize">
                {user?.provider || "credentials"}
              </span>
            </Descriptions.Item>

            <Descriptions.Item
              label={
                <span className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  Active Status
                </span>
              }
            >
              {user?.is_active ? (
                <Badge variant="success">Active</Badge>
              ) : (
                <Badge variant="danger">Deactivated</Badge>
              )}
            </Descriptions.Item>

            <Descriptions.Item
              label={
                <span className="flex items-center gap-2">
                  <Key className="w-4 h-4" />
                  Has Password
                </span>
              }
            >
              {user?.has_password ? (
                <Tag color="green">Yes</Tag>
              ) : (
                <Tag color="default">No</Tag>
              )}
            </Descriptions.Item>

            <Descriptions.Item
              label={
                <span className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  Created At
                </span>
              }
            >
              <span className="text-slate-900 dark:text-slate-100">
                {user?.created_at && formatDate(user.created_at)}
              </span>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      ),
    },
    {
      key: "clicks",
      label: (
        <span className="flex items-center gap-2">
          <History className="w-4 h-4" />
          Click History
        </span>
      ),
      children: (
        <Card className="shadow-sm">
          <Table
            columns={clickColumns}
            dataSource={clicksData?.items || []}
            rowKey="id"
            loading={clicksLoading}
            pagination={{
              current: clicksPage,
              pageSize: clicksPageSize,
              total: clicksData?.total || 0,
              onChange: (page) => {
                setClicksPage(page);
                fetchClicks(page);
              },
              showSizeChanger: false,
              showTotal: (total) => `${total} clicks`,
            }}
            locale={{
              emptyText: "No click history found for this user",
            }}
          />
        </Card>
      ),
    },
    {
      key: "actions",
      label: (
        <span className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4" />
          Admin Actions
        </span>
      ),
      children: (
        <div className="space-y-6">
          {/* Admin Notes Section */}
          <Card
            title={
              <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
                <FileText className="w-5 h-5" />
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
                className="w-full min-h-[120px] p-3 border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex justify-end">
                <Button
                  variant="primary"
                  onClick={handleSaveNotes}
                  disabled={isNotesLoading}
                >
                  {isNotesLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    "Save Notes"
                  )}
                </Button>
              </div>
            </div>
          </Card>

          {/* Admin Actions - Super Admin Only */}
          {isSuperAdmin && !isOwnProfile && (
            <Card
              title={
                <span className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
                  <ShieldAlert className="w-5 h-5" />
                  User Actions
                </span>
              }
              className="shadow-sm"
            >
              <div className="space-y-4">
                {/* Admin Access Section */}
                <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
                  <div>
                    <h4 className="font-medium text-slate-900 dark:text-slate-100">
                      Admin Access
                    </h4>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      {user?.admin_role
                        ? `User has ${user.admin_role === "super_admin" ? "super admin" : "admin"} privileges`
                        : "User does not have admin access"}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {!user?.admin_role && (
                      <Button
                        variant="primary"
                        onClick={() => setShowGrantAdminModal(true)}
                      >
                        <UserCog className="w-4 h-4" />
                        Grant Admin
                      </Button>
                    )}
                    {user?.admin_role && (
                      <Button
                        variant="outline"
                        onClick={() => setShowRevokeAdminModal(true)}
                        className="text-red-600 border-red-300 hover:bg-red-50 dark:hover:bg-red-900/20"
                      >
                        <ShieldAlert className="w-4 h-4" />
                        Revoke Admin
                      </Button>
                    )}
                  </div>
                </div>

                {/* Account Status Section */}
                <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
                  <div>
                    <h4 className="font-medium text-slate-900 dark:text-slate-100">
                      Account Status
                    </h4>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      {user?.is_active
                        ? "User account is currently active"
                        : "User account has been deactivated"}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {user?.is_active && (
                      <Button
                        variant="outline"
                        onClick={() => setShowDeactivateModal(true)}
                        className="text-red-600 border-red-300 hover:bg-red-50 dark:hover:bg-red-900/20"
                      >
                        <Ban className="w-4 h-4" />
                        Deactivate
                      </Button>
                    )}
                    {!user?.is_active && (
                      <Button
                        variant="primary"
                        onClick={() => setShowReactivateModal(true)}
                      >
                        <RotateCcw className="w-4 h-4" />
                        Reactivate
                      </Button>
                    )}
                  </div>
                </div>

                {/* Password Reset Section */}
                <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
                  <div>
                    <h4 className="font-medium text-slate-900 dark:text-slate-100">
                      Password
                    </h4>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      Password reset email delivery is not configured yet
                    </p>
                  </div>
                  <Popconfirm
                    title="Reset Password"
                    description="Record a password reset request for this user?"
                    onConfirm={handleResetPassword}
                    okText="Record request"
                    cancelText="Cancel"
                    okButtonProps={{ loading: isActionLoading }}
                  >
                    <Button variant="outline">
                      <KeyRound className="w-4 h-4" />
                      Reset Password
                    </Button>
                  </Popconfirm>
                </div>

                {/* Delete User Section */}
                <div className="flex items-center justify-between p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                  <div>
                    <h4 className="font-medium text-red-900 dark:text-red-100">
                      Danger Zone
                    </h4>
                    <p className="text-sm text-red-700 dark:text-red-300">
                      Permanently delete this user and all associated data
                    </p>
                  </div>
                  <Popconfirm
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
                      className="text-red-600 border-red-300 hover:bg-red-100 dark:hover:bg-red-900/40"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete User
                    </Button>
                  </Popconfirm>
                </div>
              </div>
            </Card>
          )}

          {/* Self-action warning */}
          {isOwnProfile && (
            <Alert type="info">
              You cannot modify your own admin status or account activation.
            </Alert>
          )}
        </div>
      ),
    },
  ];

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Spin size="large" description="Loading user details..." />
      </div>
    );
  }

  // Error state
  if (isError || !user) {
    return (
      <Result
        status="404"
        title="User Not Found"
        subTitle="The requested user could not be found."
        extra={
          <Button variant="primary" onClick={() => router.push("/admin/users")}>
            Back to Users
          </Button>
        }
      />
    );
  }

  return (
    <>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Title level={3} style={{ margin: 0 }}>
              User: {user.name || user.email}
            </Title>
          </div>
          <Button variant="secondary" onClick={() => router.push("/admin/users")}>
            Back to Users
          </Button>
        </div>

        {/* Error Alert */}
        {actionError && (
          <Alert type="error" className="mb-4">
            {actionError}
          </Alert>
        )}

        {/* Tabs */}
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </div>

      {/* Grant Admin Modal */}
      <Modal
        isOpen={showGrantAdminModal}
        onClose={() => {
          setShowGrantAdminModal(false);
          setGrantRole("admin");
          setGrantNotes("");
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
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Admin Role
            </label>
            <SingleSelect
              options={[
                { value: "admin", label: "Admin" },
                { value: "super_admin", label: "Super Admin" },
              ]}
              value={grantRole}
              onChange={setGrantRole}
              placeholder="Select role"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
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
              {isActionLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                "Grant Access"
              )}
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
            Are you sure you want to revoke admin access from{" "}
            <strong>{user.email}</strong>?
          </p>

          <Alert type="warning">
            This action will remove all admin privileges from this user. They will
            no longer be able to access the admin panel.
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
              {isActionLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                "Revoke Access"
              )}
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
            This will prevent the user from logging in and accessing their account.
            The user can be reactivated later.
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
              {isActionLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                "Deactivate"
              )}
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
            This will restore the user&apos;s access to their account. They will be able
            to log in again.
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
              {isActionLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                "Reactivate"
              )}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
