'use client';

import Modal from './Modal';

interface PrivacyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function PrivacyModal({ isOpen, onClose }: PrivacyModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Privacy Policy" size="lg">
      <div className="space-y-5">
        <p className="dark:text-md-on-surface-variant text-sm text-slate-700">
          We only collect data needed to run InternNexus and improve job matching. We do not sell
          personal data.
        </p>

        <section className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-4">
          <h4 className="dark:text-md-on-surface mb-2 text-sm font-semibold text-slate-800">
            What we collect
          </h4>
          <ul className="dark:text-md-on-surface-variant list-disc space-y-1 pl-5 text-sm text-slate-700">
            <li>Account info: name, email, and auth provider details.</li>
            <li>Profile info you add: skills, preferred locations, and optional resume.</li>
            <li>
              Usage events: saved jobs, applied markers, and product analytics for reliability.
            </li>
          </ul>
        </section>

        <section className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-4">
          <h4 className="dark:text-md-on-surface mb-2 text-sm font-semibold text-slate-800">
            How your data is used
          </h4>
          <ul className="dark:text-md-on-surface-variant list-disc space-y-1 pl-5 text-sm text-slate-700">
            <li>To authenticate your account and secure access.</li>
            <li>To power search, recommendations, and resume-based matching.</li>
            <li>To monitor abuse, debug issues, and improve system performance.</li>
          </ul>
        </section>

        <section className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-4">
          <h4 className="dark:text-md-on-surface mb-2 text-sm font-semibold text-slate-800">
            Your control
          </h4>
          <p className="dark:text-md-on-surface-variant text-sm text-slate-700">
            You can update profile fields, remove your resume, or delete your account at any time
            from settings.
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
