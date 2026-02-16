"use client";

import { useEffect, useCallback, useRef } from "react";
import JobDetailPanel from "./JobDetailPanel";
import type { Job } from "@/lib/types";

interface JobDetailPanelContainerProps {
  job: Job | null;
  isLoading?: boolean;
  onClose: () => void;
  triggerRef?: React.RefObject<HTMLElement | null>;
}

export function JobDetailPanelContainer({
  job,
  isLoading = false,
  onClose,
  triggerRef,
}: JobDetailPanelContainerProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleClose();
      }
    };

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== "Tab" || !modalRef.current) return;

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

    document.addEventListener("keydown", handleEscape);
    document.addEventListener("keydown", handleTab);

    // Only lock scroll on mobile
    const isMobile = window.innerWidth < 1024;
    if (isMobile) {
      document.body.style.overflow = "hidden";
    }

    setTimeout(() => {
      const focusableElements = modalRef.current?.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      (focusableElements?.[0] as HTMLElement)?.focus();
    }, 0);

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.removeEventListener("keydown", handleTab);
      if (isMobile) {
        document.body.style.overflow = "";
      }
      previousActiveElement.current?.focus();
      triggerRef?.current?.focus();
    };
  }, [handleClose, triggerRef]);

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
      <div
        ref={modalRef}
        className="fixed inset-4 z-50 flex lg:hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="job-detail-title"
      >
        <div className="w-full rounded-2xl bg-white dark:bg-md-surface-container-low">
          <JobDetailPanel job={job} isLoading={isLoading} onClose={handleClose} />
        </div>
      </div>

      <div className="hidden sticky top-20 h-[calc(100vh-7rem)] w-1/2 min-w-[400px] lg:block">
        <JobDetailPanel job={job} isLoading={isLoading} onClose={handleClose} />
      </div>
    </>
  );
}
