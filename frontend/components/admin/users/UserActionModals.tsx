import { Loader2, UserCog, ShieldAlert, Ban, RotateCcw } from 'lucide-react';
import { Button, Alert, IconContainer, Input } from '@/components/ui';
import { SingleSelect } from '@/components/ui/SingleSelect';
import { Modal } from '@/components/modals';
import { type AdminUser } from '@/app/actions/admin';

interface UserActionModalsProps {
  readonly user: AdminUser;
  readonly showGrantAdminModal: boolean;
  readonly showRevokeAdminModal: boolean;
  readonly showDeactivateModal: boolean;
  readonly showReactivateModal: boolean;
  readonly grantRole: string;
  readonly grantNotes: string;
  readonly isActionLoading: boolean;
  readonly actionError: string | null;
  readonly onCloseGrantModal: () => void;
  readonly onCloseRevokeModal: () => void;
  readonly onCloseDeactivateModal: () => void;
  readonly onCloseReactivateModal: () => void;
  readonly onGrantRoleChange: (role: string) => void;
  readonly onGrantNotesChange: (notes: string) => void;
  readonly onGrantAdmin: () => void;
  readonly onRevokeAdmin: () => void;
  readonly onDeactivate: () => void;
  readonly onReactivate: () => void;
}

export function UserActionModals({
  user,
  showGrantAdminModal,
  showRevokeAdminModal,
  showDeactivateModal,
  showReactivateModal,
  grantRole,
  grantNotes,
  isActionLoading,
  actionError,
  onCloseGrantModal,
  onCloseRevokeModal,
  onCloseDeactivateModal,
  onCloseReactivateModal,
  onGrantRoleChange,
  onGrantNotesChange,
  onGrantAdmin,
  onRevokeAdmin,
  onDeactivate,
  onReactivate,
}: UserActionModalsProps) {
  return (
    <>
      <Modal
        isOpen={showGrantAdminModal}
        onClose={onCloseGrantModal}
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
              onChange={onGrantRoleChange}
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
              onChange={(e) => onGrantNotesChange(e.target.value)}
              placeholder="Reason for granting admin access..."
            />
          </div>

          {actionError && <Alert type="error">{actionError}</Alert>}

          <div className="flex gap-3 pt-4">
            <Button variant="secondary" onClick={onCloseGrantModal} className="flex-1">
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={onGrantAdmin}
              disabled={isActionLoading}
              className="flex-1"
            >
              {isActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Grant Access'}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={showRevokeAdminModal}
        onClose={onCloseRevokeModal}
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

          {actionError && <Alert type="error">{actionError}</Alert>}

          <div className="flex gap-3 pt-4">
            <Button variant="secondary" onClick={onCloseRevokeModal} className="flex-1">
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={onRevokeAdmin}
              disabled={isActionLoading}
              className="flex-1 bg-red-600 hover:bg-red-700"
            >
              {isActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Revoke Access'}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={showDeactivateModal}
        onClose={onCloseDeactivateModal}
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

          {actionError && <Alert type="error">{actionError}</Alert>}

          <div className="flex gap-3 pt-4">
            <Button variant="secondary" onClick={onCloseDeactivateModal} className="flex-1">
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={onDeactivate}
              disabled={isActionLoading}
              className="flex-1 bg-red-600 hover:bg-red-700"
            >
              {isActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Deactivate'}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={showReactivateModal}
        onClose={onCloseReactivateModal}
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

          {actionError && <Alert type="error">{actionError}</Alert>}

          <div className="flex gap-3 pt-4">
            <Button variant="secondary" onClick={onCloseReactivateModal} className="flex-1">
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={onReactivate}
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
