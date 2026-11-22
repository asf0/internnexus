'use client';

import LegalSection from './LegalSection';
import Modal from './Modal';

interface PrivacyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PrivacyContent() {
  return (
    <div className="space-y-6">
      <div className="border-border bg-surface-subtle rounded-lg border p-4">
        <p className="text-foreground text-sm font-semibold">Summary</p>
        <p className="text-foreground-secondary mt-1 text-sm leading-6">
          InternNexus collects the information needed to operate accounts, job-search tools, and
          resume matching. We do not sell your personal information.
        </p>
      </div>

      <LegalSection title="Information we collect">
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong>Account and profile data:</strong> email, name, profile image, sign-in provider,
            and any profile details you choose to add.
          </li>
          <li>
            <strong>Resume and matching data:</strong> uploaded file metadata, extracted resume
            text, and the numeric embedding used to compare your resume with jobs.
          </li>
          <li>
            <strong>Job-search activity:</strong> saved jobs, application markers, notifications,
            and clicks to employer application pages.
          </li>
          <li>
            <strong>Technical data:</strong> session information, a shortened hash derived from your
            IP address, browser user agent, referrer, and operational logs.
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="How we use information">
        <ul className="list-disc space-y-1 pl-5">
          <li>Authenticate users, maintain sessions, and protect the service from abuse.</li>
          <li>Provide search, saved jobs, application tracking, and resume-based matching.</li>
          <li>Measure feature reliability, investigate errors, and improve service performance.</li>
          <li>Send in-product notices related to your account or activity.</li>
        </ul>
      </LegalSection>

      <LegalSection title="Cookies and local storage">
        <p>
          InternNexus uses essential session cookies to keep you signed in. Match results and a
          match-session identifier may be stored in your browser so the experience survives
          navigation. These values can be cleared through your browser controls.
        </p>
      </LegalSection>

      <LegalSection title="When information is shared">
        <p>We share information only as needed to operate the service, including:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>With your selected sign-in provider when you use OAuth.</li>
          <li>With infrastructure or processing providers that support the application.</li>
          <li>When required by law or necessary to protect users and the service.</li>
        </ul>
        <p>
          Opening an application link takes you to an employer or applicant-tracking system. Their
          privacy practices apply after you leave InternNexus.
        </p>
      </LegalSection>

      <LegalSection title="Storage, security, and retention">
        <p>
          Passwords are hashed, and sensitive resume text and connected-account tokens are stored in
          encrypted form. No system is completely secure, but access is limited and reasonable
          safeguards are used.
        </p>
        <p>
          Data is kept while your account is active and as needed for service operation, security,
          and legal obligations. Account deletion de-identifies core account information and
          disconnects sign-in providers; limited operational records may remain where necessary.
        </p>
      </LegalSection>

      <LegalSection title="Your choices">
        <p>
          You can edit profile details and remove an uploaded resume from Profile. You can delete
          your account from Settings. You may also disconnect InternNexus through your OAuth
          provider&apos;s account controls.
        </p>
      </LegalSection>

      <div className="border-border text-foreground-muted flex flex-col gap-1 border-t pt-4 text-xs sm:flex-row sm:items-center sm:justify-between">
        <p>Effective and last updated: July 3, 2026</p>
        <a
          href="https://github.com/asf0/internnexus/issues"
          target="_blank"
          rel="noopener noreferrer"
          className="text-foreground decoration-border font-medium underline underline-offset-4"
        >
          Privacy questions
        </a>
      </div>
    </div>
  );
}

export default function PrivacyModal({ isOpen, onClose }: Readonly<PrivacyModalProps>) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Privacy Policy" size="xl">
      <PrivacyContent />
    </Modal>
  );
}
