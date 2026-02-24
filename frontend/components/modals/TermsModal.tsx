"use client";

import Modal from "./Modal";

interface TermsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function TermsModal({ isOpen, onClose }: TermsModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Terms of Service" size="lg">
      <div className="space-y-5">
        <p className="text-sm text-slate-700 dark:text-md-on-surface-variant">
          By using InternNexus, you agree to use the service responsibly and in compliance with applicable laws.
        </p>

        <section className="rounded-lg bg-slate-50 p-4 dark:bg-md-surface-container-high">
          <h4 className="mb-2 text-sm font-semibold text-slate-800 dark:text-md-on-surface">
            Acceptable use
          </h4>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-md-on-surface-variant">
            <li>Do not attempt unauthorized access, scraping abuse, or service disruption.</li>
            <li>Do not upload unlawful, harmful, or infringing content.</li>
            <li>Use matching and analytics features for legitimate job-search activity.</li>
          </ul>
        </section>

        <section className="rounded-lg bg-slate-50 p-4 dark:bg-md-surface-container-high">
          <h4 className="mb-2 text-sm font-semibold text-slate-800 dark:text-md-on-surface">
            Service scope and availability
          </h4>
          <p className="text-sm text-slate-700 dark:text-md-on-surface-variant">
            Job listings are aggregated from third-party sources and may change or be removed at any time.
            We do not guarantee uninterrupted availability or completeness of external data.
          </p>
        </section>

        <section className="rounded-lg bg-slate-50 p-4 dark:bg-md-surface-container-high">
          <h4 className="mb-2 text-sm font-semibold text-slate-800 dark:text-md-on-surface">
            Limitation of liability
          </h4>
          <p className="text-sm text-slate-700 dark:text-md-on-surface-variant">
            InternNexus is provided on an &quot;as is&quot; basis. We are not liable for indirect or consequential damages
            resulting from use of the service.
          </p>
        </section>

        <div className="border-t border-slate-200 pt-4 dark:border-md-outline-variant">
          <p className="text-xs text-slate-500 dark:text-md-on-surface-variant">
            Last updated: February 24, 2026
          </p>
        </div>
      </div>
    </Modal>
  );
}
