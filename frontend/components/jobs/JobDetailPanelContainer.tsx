'use client';

import { useEffect, useCallback, useRef } from 'react';
import JobDetailPanel from './JobDetailPanel';
import type { JobSummary } from '@/lib/types';
import type { JobDetailView } from './fetchJobDetail';

interface JobDetailPanelContainerProps {
  readonly job: JobSummary | null;
  readonly detail: JobDetailView | null;
  readonly isLoading?: boolean;
  readonly error: string | null;
  readonly isUnavailable: boolean;
  readonly onRetry: () => void;
  readonly onClose: () => void;
  readonly isAuthenticated: boolean;
  readonly onRequireAuthForApply: (applyUrl: string, jobId: string) => void;
  readonly isApplied?: boolean;
  readonly isAppliedPending?: boolean;
  readonly onToggleApplied?: (shouldApply: boolean) => void;
  readonly onApply?: (jobId: string, applyUrl: string) => Promise<void>;
  readonly triggerRef?: React.RefObject<HTMLElement | null>;
}

export function JobDetailPanelContainer({
  job,
  detail,
  isLoading = false,
  error,
  isUnavailable,
  onRetry,
  onClose,
  isAuthenticated,
  onRequireAuthForApply,
  isApplied,
  isAppliedPending,
  onToggleApplied,
  onApply,
  triggerRef,
}: JobDetailPanelContainerProps) {
  const modalRef = useRef<HTMLDialogElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!job) return;

    previousActiveElement.current = document.activeElement as HTMLElement;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose();
      }
    };

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab' || !modalRef.current) return;

      const focusableElements = modalRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const firstElement = focusableElements[0] as HTMLElement;
      const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    };

    document.addEventListener('keydown', handleEscape);
    document.addEventListener('keydown', handleTab);

    // Only lock scroll on mobile
    const isMobile = window.innerWidth < 1024;
    if (isMobile) {
      document.body.style.overflow = 'hidden';
    }

    setTimeout(() => {
      const focusableElements = modalRef.current?.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      (focusableElements?.[0] as HTMLElement)?.focus();
    }, 0);

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.removeEventListener('keydown', handleTab);
      if (isMobile) {
        document.body.style.overflow = '';
      }
      previousActiveElement.current?.focus();
      triggerRef?.current?.focus();
    };
  }, [handleClose, job, triggerRef]);

  if (!job && !isLoading) {
    return null;
  }

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/50 lg:hidden"
        onClick={handleClose}
        aria-hidden="true"
      />
      <dialog
        open
        ref={modalRef}
        className="fixed inset-4 z-50 flex lg:hidden"
        aria-modal="true"
        aria-labelledby="job-detail-title"
      >
        <div className="bg-surface w-full rounded-2xl">
          <JobDetailPanel
            job={job}
            detail={detail}
            isLoading={isLoading}
            error={error}
            isUnavailable={isUnavailable}
            onRetry={onRetry}
            onClose={handleClose}
            isAuthenticated={isAuthenticated}
            onRequireAuthForApply={onRequireAuthForApply}
            isApplied={isApplied}
            isAppliedPending={isAppliedPending}
            onToggleApplied={onToggleApplied}
            onApply={onApply}
          />
        </div>
      </dialog>

      <div className="sticky top-20 hidden h-[calc(100vh-7rem)] w-1/2 min-w-[400px] lg:block">
        <JobDetailPanel
          job={job}
          detail={detail}
          isLoading={isLoading}
          error={error}
          isUnavailable={isUnavailable}
          onRetry={onRetry}
          onClose={handleClose}
          isAuthenticated={isAuthenticated}
          onRequireAuthForApply={onRequireAuthForApply}
          isApplied={isApplied}
          isAppliedPending={isAppliedPending}
          onToggleApplied={onToggleApplied}
          onApply={onApply}
        />
      </div>
    </>
  );
}
