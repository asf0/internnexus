'use client';

import { ReactNode, useState, cloneElement, isValidElement, type ReactElement } from 'react';
import { Modal } from '@/components/modals';
import { Button } from '@/components/ui';

interface AdminPopconfirmProps {
  readonly title: ReactNode;
  readonly description?: ReactNode;
  readonly onConfirm: () => void | Promise<void>;
  readonly okText?: string;
  readonly cancelText?: string;
  readonly okButtonProps?: { loading?: boolean; danger?: boolean };
  readonly children: ReactElement<{ onClick?: () => void }>;
}

export function AdminPopconfirm({
  title,
  description,
  onConfirm,
  okText = 'OK',
  cancelText = 'Cancel',
  okButtonProps,
  children,
}: AdminPopconfirmProps) {
  const [open, setOpen] = useState(false);

  const handleOpen = () => setOpen(true);
  const handleClose = () => setOpen(false);

  const trigger = isValidElement(children)
    ? cloneElement(children, { onClick: handleOpen })
    : children;

  return (
    <>
      {trigger}
      <Modal
        isOpen={open}
        onClose={handleClose}
        title={<span className="text-lg font-semibold">{title}</span>}
        size="sm"
      >
        <div className="space-y-4">
          {description && (
            <p className="dark:text-md-on-surface-variant text-slate-600">{description}</p>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={handleClose}>
              {cancelText}
            </Button>
            <Button
              variant="primary"
              onClick={async () => {
                await onConfirm();
                if (!okButtonProps?.loading) setOpen(false);
              }}
              disabled={okButtonProps?.loading}
              className={okButtonProps?.danger ? 'bg-red-600 hover:bg-red-700' : ''}
            >
              {okText}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
