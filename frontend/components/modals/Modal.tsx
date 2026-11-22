'use client';

import { ReactNode, useEffect, useId } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly title?: ReactNode;
  readonly children: ReactNode;
  readonly size?: 'sm' | 'md' | 'lg' | 'xl';
  readonly showCloseButton?: boolean;
}

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-2xl',
};

export default function Modal({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
  showCloseButton = true,
}: ModalProps) {
  const titleId = useId();

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    globalThis.addEventListener('keydown', handleEscape);
    return () => globalThis.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-4">
      {/* Backdrop */}
      <button
        type="button"
        className="absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-label="Close modal"
      />

      {/* Modal Card */}
      <dialog
        open
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        className={`border-border bg-surface relative mx-2 flex w-full flex-col rounded-xl border shadow-2xl sm:mx-0 ${sizeClasses[size]} z-10 max-h-[92vh] sm:max-h-[80vh]`}
      >
        {/* Close Button */}
        {showCloseButton && (
          <button
            type="button"
            onClick={onClose}
            className="text-foreground-muted hover:bg-surface-subtle hover:text-foreground absolute top-4 right-4 z-20 rounded-lg p-1 transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        )}

        {/* Header */}
        {title && (
          <div className="border-border shrink-0 border-b px-4 pt-4 pb-3 sm:px-6 sm:pt-6 sm:pb-4">
            <h2 id={titleId} className="text-foreground text-xl font-bold sm:text-2xl">
              {title}
            </h2>
          </div>
        )}

        {/* Content */}
        <div className="text-foreground-secondary flex-1 overflow-y-auto px-4 py-3 sm:px-6 sm:py-4">
          {children}
        </div>
      </dialog>
    </div>
  );
}
