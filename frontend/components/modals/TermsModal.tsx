'use client';

import Modal from './Modal';

interface TermsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function TermsModal({ isOpen, onClose }: TermsModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Terms of Service" size="lg">
      <div className="space-y-5">
        <p className="dark:text-md-on-surface-variant text-sm text-slate-700">
          By using InternNexus, you agree to use the service responsibly and in compliance with
          applicable laws.
        </p>

        <section className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-4">
          <h4 className="dark:text-md-on-surface mb-2 text-sm font-semibold text-slate-800">
            Acceptable use
          </h4>
          <ul className="dark:text-md-on-surface-variant list-disc space-y-1 pl-5 text-sm text-slate-700">
            <li>Do not attempt unauthorized access, scraping abuse, or service disruption.</li>
            <li>Do not upload unlawful, harmful, or infringing content.</li>
            <li>Use matching and analytics features for legitimate job-search activity.</li>
          </ul>
        </section>

        <section className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-4">
          <h4 className="dark:text-md-on-surface mb-2 text-sm font-semibold text-slate-800">
            Service scope and availability
          </h4>
          <p className="dark:text-md-on-surface-variant text-sm text-slate-700">
            Job listings are aggregated from third-party sources and may change or be removed at any
            time. We do not guarantee uninterrupted availability or completeness of external data.
          </p>
        </section>

        <section className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-4">
          <h4 className="dark:text-md-on-surface mb-2 text-sm font-semibold text-slate-800">
            Limitation of liability
          </h4>
          <p className="dark:text-md-on-surface-variant text-sm text-slate-700">
            InternNexus is provided on an &quot;as is&quot; basis. We are not liable for indirect or
            consequential damages resulting from use of the service.
          </p>
        </section>

        <div className="dark:border-md-outline-variant border-t border-slate-200 pt-4">
          <p className="dark:text-md-on-surface-variant text-xs text-slate-500">
            Last updated: February 24, 2026
          </p>
        </div>
      </div>
    </Modal>
  );
}
