'use client';

import LegalSection from './LegalSection';
import Modal from './Modal';

interface TermsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function TermsContent() {
  return (
    <div className="space-y-6">
      <div className="border-border bg-surface-subtle rounded-lg border p-4">
        <p className="text-foreground-secondary text-sm leading-6">
          By accessing or using InternNexus, you agree to these terms. If you do not agree, do not
          use the service.
        </p>
      </div>

      <LegalSection title="Using InternNexus">
        <p>
          You must be legally able to enter into these terms and provide accurate account
          information. You are responsible for activity under your account and for keeping your
          sign-in credentials secure.
        </p>
        <p>
          InternNexus provides job discovery, organization, and matching tools. It is not an
          employer, recruiter, staffing agency, or party to any application or employment
          relationship.
        </p>
      </LegalSection>

      <LegalSection title="Job listings and matching">
        <p>
          Listings come from third-party company sites and applicant-tracking systems. Details may
          be delayed, incomplete, changed, or removed without notice. Confirm compensation,
          eligibility, location, deadlines, and other requirements with the employer.
        </p>
        <p>
          Search rankings and resume-match scores are automated estimates for discovery only. They
          do not represent an employer&apos;s assessment and do not guarantee an interview, offer,
          or outcome.
        </p>
      </LegalSection>

      <LegalSection title="Acceptable use">
        <p>You may not:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>Break the law, infringe rights, or upload malicious or unlawful material.</li>
          <li>
            Probe, bypass, or interfere with authentication, rate limits, or security controls.
          </li>
          <li>
            Use automation in a way that overloads, disrupts, or extracts the service at scale.
          </li>
          <li>Impersonate others or use the service for fraudulent job or recruiting activity.</li>
        </ul>
      </LegalSection>

      <LegalSection title="Third-party services">
        <p>
          InternNexus links to services it does not control, including employer career sites,
          applicant-tracking systems, and sign-in providers. Their terms and policies apply to your
          use of those services. A link does not imply endorsement.
        </p>
      </LegalSection>

      <LegalSection title="Availability and account action">
        <p>
          The service may be changed, interrupted, or discontinued. Access may be limited or
          suspended to address security, abuse, legal requirements, or material violations of these
          terms. You may stop using InternNexus and delete your account at any time.
        </p>
      </LegalSection>

      <LegalSection title="Disclaimers and liability">
        <p>
          InternNexus is provided &quot;as is&quot; and &quot;as available&quot; without warranties
          of accuracy, availability, fitness for a particular purpose, or non-infringement, to the
          extent permitted by law.
        </p>
        <p>
          To the extent permitted by law, InternNexus and its maintainer are not liable for
          indirect, incidental, special, consequential, or exemplary damages, or for losses arising
          from third-party listings, employment decisions, unauthorized access, or service
          interruption.
        </p>
      </LegalSection>

      <div className="border-border border-t pt-5">
        <h3 className="text-foreground text-sm font-semibold">Changes to these terms</h3>
        <p className="text-foreground-secondary mt-2 text-sm leading-6">
          These terms may be updated as the service changes. The effective date below identifies the
          current version. Continued use after an update means you accept the revised terms.
        </p>
      </div>

      <div className="border-border text-foreground-muted flex flex-col gap-1 border-t pt-4 text-xs sm:flex-row sm:items-center sm:justify-between">
        <p>Effective and last updated: July 3, 2026</p>
        <a
          href="https://github.com/asf0/internnexus/issues"
          target="_blank"
          rel="noopener noreferrer"
          className="text-foreground decoration-border font-medium underline underline-offset-4"
        >
          Terms questions
        </a>
      </div>
    </div>
  );
}

export default function TermsModal({ isOpen, onClose }: Readonly<TermsModalProps>) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Terms of Service" size="xl">
      <TermsContent />
    </Modal>
  );
}
