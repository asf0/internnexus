import {
  Loader2,
  ShieldAlert,
  UserCog,
  Ban,
  RotateCcw,
  KeyRound,
  Trash2,
  FileText,
} from 'lucide-react';
import { Button, Alert } from '@/components/ui';
import { AdminCard, AdminPopconfirm } from '@/components/admin/ui';
import { type AdminUser } from '@/app/actions/admin';
import { type CurrentAdminInfo } from './types';

interface UserActionsTabProps {
  readonly user: AdminUser;
  readonly currentAdmin: CurrentAdminInfo | null;
  readonly notes: string;
  readonly isNotesLoading: boolean;
  readonly isActionLoading: boolean;
  readonly onNotesChange: (notes: string) => void;
  readonly onSaveNotes: () => void;
  readonly onGrantAdminClick: () => void;
  readonly onRevokeAdminClick: () => void;
  readonly onDeactivateClick: () => void;
  readonly onReactivateClick: () => void;
  readonly onResetPassword: () => void;
  readonly onDeleteUser: () => void;
}

function adminAccessDescription(role: UserActionsTabProps['user']['admin_role']): string {
  if (!role) return 'User does not have admin access';
  return `User has ${role === 'super_admin' ? 'super admin' : 'admin'} privileges`;
}

export function UserActionsTab({
  user,
  currentAdmin,
  notes,
  isNotesLoading,
  isActionLoading,
  onNotesChange,
  onSaveNotes,
  onGrantAdminClick,
  onRevokeAdminClick,
  onDeactivateClick,
  onReactivateClick,
  onResetPassword,
  onDeleteUser,
}: UserActionsTabProps) {
  const isSuperAdmin = currentAdmin?.role === 'super_admin';
  const isOwnProfile = currentAdmin?.id === user.id;

  return (
    <div className="space-y-6">
      <AdminCard
        title={
          <span className="text-foreground flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Admin Notes
          </span>
        }
        className="shadow-sm"
      >
        <div className="space-y-4">
          <textarea
            value={notes}
            onChange={(e) => onNotesChange(e.target.value)}
            placeholder="Add notes about this user..."
            className="border-border bg-surface text-foreground focus:ring-accent min-h-[120px] w-full resize-y rounded-lg border p-3 focus:ring-2 focus:outline-none"
          />
          <div className="flex justify-end">
            <Button variant="primary" onClick={onSaveNotes} disabled={isNotesLoading}>
              {isNotesLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save Notes'}
            </Button>
          </div>
        </div>
      </AdminCard>

      {isSuperAdmin && !isOwnProfile && (
        <AdminCard
          title={
            <span className="text-foreground flex items-center gap-2">
              <ShieldAlert className="h-5 w-5" />
              User Actions
            </span>
          }
          className="shadow-sm"
        >
          <div className="space-y-4">
            <div className="bg-surface-subtle flex items-center justify-between rounded-lg p-4">
              <div>
                <h4 className="text-foreground font-medium">Admin Access</h4>
                <p className="text-foreground-muted text-sm">
                  {adminAccessDescription(user.admin_role)}
                </p>
              </div>
              <div className="flex gap-2">
                {!user.admin_role && (
                  <Button variant="primary" onClick={onGrantAdminClick}>
                    <UserCog className="h-4 w-4" />
                    Grant Admin
                  </Button>
                )}
                {user.admin_role && (
                  <Button
                    variant="outline"
                    onClick={onRevokeAdminClick}
                    className="border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    <ShieldAlert className="h-4 w-4" />
                    Revoke Admin
                  </Button>
                )}
              </div>
            </div>

            <div className="bg-surface-subtle flex items-center justify-between rounded-lg p-4">
              <div>
                <h4 className="text-foreground font-medium">Account Status</h4>
                <p className="text-foreground-muted text-sm">
                  {user.is_active
                    ? 'User account is currently active'
                    : 'User account has been deactivated'}
                </p>
              </div>
              <div className="flex gap-2">
                {user.is_active && (
                  <Button
                    variant="outline"
                    onClick={onDeactivateClick}
                    className="border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    <Ban className="h-4 w-4" />
                    Deactivate
                  </Button>
                )}
                {!user.is_active && (
                  <Button variant="primary" onClick={onReactivateClick}>
                    <RotateCcw className="h-4 w-4" />
                    Reactivate
                  </Button>
                )}
              </div>
            </div>

            <div className="bg-surface-subtle flex items-center justify-between rounded-lg p-4">
              <div>
                <h4 className="text-foreground font-medium">Password</h4>
                <p className="text-foreground-muted text-sm">
                  Password reset email delivery is not configured yet
                </p>
              </div>
              <AdminPopconfirm
                title="Reset Password"
                description="Record a password reset request for this user?"
                onConfirm={onResetPassword}
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

            <div className="dark:border-danger/40 dark:bg-surface-inset flex items-center justify-between rounded-lg border border-red-200 bg-red-50 p-4">
              <div>
                <h4 className="dark:text-danger font-medium text-red-900">Danger Zone</h4>
                <p className="dark:text-danger text-sm text-red-700">
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
                onConfirm={onDeleteUser}
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
        <Alert type="info">You cannot modify your own admin status or account activation.</Alert>
      )}
    </div>
  );
}
