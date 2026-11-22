import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import RelatedJobs from '@/components/jobs/RelatedJobs';
import type { JobSummary } from '@/lib/types';

function job(overrides: Partial<JobSummary> & { id: string }): JobSummary {
  return {
    source: 'greenhouse',
    title: 'Engineer',
    company: 'Acme',
    location: 'London, UK',
    city: 'London',
    state: null,
    country: 'UK',
    apply_url: 'https://example.com/apply',
    job_category: 'engineering',
    job_type: 'full_time',
    work_mode: 'hybrid',
    posted_at: '2026-09-01T00:00:00Z',
    is_active: true,
    ...overrides,
  };
}

describe('RelatedJobs', () => {
  it('renders nothing when there are no related jobs', () => {
    const { container } = render(<RelatedJobs company="Acme" category="engineering" jobs={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('splits same-company and same-category jobs and links to hubs', () => {
    const jobs = [
      job({ id: 'a', company: 'Acme', title: 'Backend at Acme' }),
      job({ id: 'b', company: 'Other', title: 'Backend at Other' }),
    ];
    const { container } = render(<RelatedJobs company="Acme" category="engineering" jobs={jobs} />);

    const links = Array.from(container.querySelectorAll('a')).map((a) => a.getAttribute('href'));
    expect(links).toContain('/jobs/a');
    expect(links).toContain('/jobs/b');
    expect(links).toContain('/companies/acme');
    expect(links).toContain('/categories/engineering');
    expect(container.textContent).toContain('More jobs at Acme');
  });

  it('caps each section at five links', () => {
    const jobs = Array.from({ length: 8 }, (_, i) => job({ id: `j${i}`, company: 'Acme' }));
    const { container } = render(<RelatedJobs company="Acme" category="engineering" jobs={jobs} />);
    const jobLinks = container.querySelectorAll('a[href^="/jobs/"]');
    expect(jobLinks.length).toBe(5);
  });
});
