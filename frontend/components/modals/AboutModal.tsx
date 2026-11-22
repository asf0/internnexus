'use client';

import Link from 'next/link';
import Modal from './Modal';

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const features = [
  {
    title: 'Unified search',
    description: 'Search listings from company career sites in one place.',
  },
  {
    title: 'Useful filters',
    description: 'Narrow results by company, location, category, work mode, and recency.',
  },
  {
    title: 'Resume matching',
    description: 'Compare your resume with job descriptions using semantic relevance.',
  },
  {
    title: 'Personal workspace',
    description: 'Save opportunities and keep track of roles you have applied to.',
  },
];

export function AboutContent() {
  return (
    <div className="space-y-7">
      <div className="border-border border-b pb-6">
        <p className="text-foreground text-xl font-semibold tracking-tight">
          A focused workspace for finding your next opportunity.
        </p>
        <p className="text-foreground-secondary mt-3 max-w-2xl text-sm leading-6">
          InternNexus brings job listings, practical search tools, and application tracking together
          so you can spend less time navigating career sites and more time evaluating relevant
          roles.
        </p>
      </div>

      <section>
        <h3 className="text-foreground text-sm font-semibold">What InternNexus provides</h3>
        <div className="border-border mt-3 grid overflow-hidden rounded-lg border sm:grid-cols-2">
          {features.map((feature, index) => (
            <div
              key={feature.title}
              className={[
                'p-4',
                index > 0 ? 'border-border border-t' : '',
                index === 1 ? 'sm:border-t-0 sm:border-l' : '',
                index === 2 ? 'sm:border-l-0' : '',
                index === 3 ? 'sm:border-l' : '',
              ].join(' ')}
            >
              <h4 className="text-foreground text-sm font-medium">{feature.title}</h4>
              <p className="text-foreground-secondary mt-1 text-sm leading-5">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-border border-t pt-6">
        <h3 className="text-foreground text-sm font-semibold">Independent and open source</h3>
        <p className="text-foreground-secondary mt-2 text-sm leading-6">
          InternNexus is an independent discovery tool maintained by asf0. It is not an employer or
          recruiting agency. Always confirm role details on the employer&apos;s website.
        </p>
        <Link
          href="https://github.com/asf0/internnexus"
          target="_blank"
          rel="noopener noreferrer"
          className="text-foreground decoration-border hover:decoration-foreground mt-3 inline-block text-sm font-medium underline underline-offset-4"
        >
          View the project on GitHub
        </Link>
      </section>
    </div>
  );
}

export default function AboutModal({ isOpen, onClose }: Readonly<AboutModalProps>) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="About InternNexus" size="xl">
      <AboutContent />
    </Modal>
  );
}
