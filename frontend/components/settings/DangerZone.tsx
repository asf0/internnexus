'use client';

import { Trash2, AlertTriangle, Loader2 } from 'lucide-react';
import { Button, Input, IconContainer } from '@/components/ui';
import { Modal } from '@/components/modals';
import { DELETE_CONFIRM_TEXT } from '@/lib/constants';

interface DangerZoneProps {
  showDeleteModal: boolean;
  deleteConfirmText: string;
  isDeleting: boolean;
  onDeleteModalOpen: () => void;
  onDeleteModalClose: () => void;
  onDeleteConfirmTextChange: (text: string) => void;
  onDeleteAccount: () => void;
}

export function DangerZone({
  showDeleteModal,
  deleteConfirmText,
  isDeleting,
  onDeleteModalOpen,
  onDeleteModalClose,
  onDeleteConfirmTextChange,
  onDeleteAccount,
}: Readonly<DangerZoneProps>) {
  return (
    <>
      <div className="dark:border-danger/40 dark:bg-surface-inset rounded-xl border-2 border-red-200 bg-red-50 p-6">
        <div className="mb-4 flex items-center gap-3">
          <IconContainer icon={AlertTriangle} color="red" />
          <div>
            <h2 className="dark:text-danger text-xl font-semibold text-red-900">Danger Zone</h2>
            <p className="dark:text-danger text-sm text-red-800">Irreversible actions</p>
          </div>
        </div>

        <h3 className="dark:text-danger mb-2 text-lg font-semibold text-red-900">Delete Account</h3>
        <p className="dark:text-danger mb-4 text-red-700">
          This action deactivates and de-identifies your account and disconnects its sign-in
          methods. Some security and operational records may be retained where necessary.
        </p>
        <Button
          variant="primary"
          onClick={onDeleteModalOpen}
          className="bg-red-600 text-white hover:bg-red-700 dark:text-white"
        >
          <Trash2 className="h-4 w-4" />
          Delete Account
        </Button>
      </div>

      <Modal
        isOpen={showDeleteModal}
        onClose={onDeleteModalClose}
        title={
          <div className="flex items-center gap-3">
            <IconContainer icon={AlertTriangle} color="red" />
            <span>Delete Account</span>
          </div>
        }
        size="md"
      >
        <p className="text-foreground-secondary mb-4">
          This action cannot be undone. Your account will be deactivated, identifying profile
          information will be removed, and connected sign-in methods will be disconnected.
        </p>

        <div className="bg-surface-subtle mb-4 rounded-lg p-4">
          <p className="text-foreground-secondary mb-2 text-sm">
            Please type <strong className="text-danger">{DELETE_CONFIRM_TEXT}</strong> to confirm:
          </p>
          <Input
            type="text"
            value={deleteConfirmText}
            onChange={(e) => onDeleteConfirmTextChange(e.target.value)}
            placeholder="Type DELETE"
          />
        </div>

        <div className="flex gap-3">
          <Button variant="secondary" onClick={onDeleteModalClose} className="flex-1">
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={onDeleteAccount}
            disabled={isDeleting || deleteConfirmText !== DELETE_CONFIRM_TEXT}
            className="flex-1 bg-red-600 text-white hover:bg-red-700 dark:text-white"
          >
            {isDeleting ? <Loader2 className="mx-auto h-4 animate-spin" /> : 'Delete Account'}
          </Button>
        </div>
      </Modal>
    </>
  );
}
