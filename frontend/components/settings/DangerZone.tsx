"use client";

import { Trash2, AlertTriangle, Loader2 } from "lucide-react";
import { Button, Input, IconContainer, Alert } from "@/components/ui";
import { Modal } from "@/components/modals";
import { DELETE_CONFIRM_TEXT } from "@/lib/constants";

interface DangerZoneProps {
  showDeleteModal: boolean;
  deleteConfirmText: string;
  isSaving: boolean;
  onDeleteModalOpen: () => void;
  onDeleteModalClose: () => void;
  onDeleteConfirmTextChange: (text: string) => void;
  onDeleteAccount: () => void;
}

export function DangerZone({
  showDeleteModal,
  deleteConfirmText,
  isSaving,
  onDeleteModalOpen,
  onDeleteModalClose,
  onDeleteConfirmTextChange,
  onDeleteAccount,
}: DangerZoneProps) {
  return (
    <>
      <div className="bg-red-50 dark:bg-red-900/10 border-2 border-red-200 dark:border-red-800 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <IconContainer icon={AlertTriangle} color="red" />
          <div>
            <h2 className="text-xl font-semibold text-red-900 dark:text-red-100">Danger Zone</h2>
            <p className="text-sm text-red-600 dark:text-red-300">Irreversible actions</p>
          </div>
        </div>

        <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">Delete Account</h3>
        <p className="text-red-700 dark:text-red-300 mb-4">
          Once you delete your account, there is no going back. This action will permanently delete your account
          and all associated data in accordance with GDPR and CCPA regulations.
        </p>
        <Button
          variant="primary"
          onClick={onDeleteModalOpen}
          className="bg-red-600 hover:bg-red-700"
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
        <p className="text-slate-600 dark:text-md-on-surface-variant mb-4">
          This action cannot be undone. This will permanently delete your account and remove your data from our
          servers.
        </p>

        <div className="bg-slate-100 dark:bg-md-surface-container-high rounded-lg p-4 mb-4">
          <p className="text-sm text-slate-700 dark:text-md-on-surface-variant mb-2">
            Please type <strong className="text-red-600">{DELETE_CONFIRM_TEXT}</strong> to confirm:
          </p>
          <Input
            type="text"
            value={deleteConfirmText}
            onChange={(e) => onDeleteConfirmTextChange(e.target.value)}
            placeholder="Type DELETE"
          />
        </div>

        <div className="flex gap-3">
          <Button
            variant="secondary"
            onClick={onDeleteModalClose}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={onDeleteAccount}
            disabled={isSaving || deleteConfirmText !== DELETE_CONFIRM_TEXT}
            className="flex-1 bg-red-600 hover:bg-red-700"
          >
            {isSaving ? <Loader2 className="h-4 h-4 animate-spin mx-auto" /> : "Delete Account"}
          </Button>
        </div>
      </Modal>
    </>
  );
}
