import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import JobDetailPanel from '@/components/jobs/JobDetailPanel';
import type { JobDetail, JobSummary } from '@/lib/types/job';

const summary: JobSummary = {
  id: '00000000-0000-0000-0000-000000000001',
  source: 'greenhouse',
  title: 'Software Intern',
  company: 'Acme',
  location: 'Remote',
  city: null,
  state: null,
  country: null,
  apply_url: 'https://example.com/apply',
  job_category: 'software_engineering',
  job_type: 'internship',
  work_mode: 'remote',
  posted_at: null,
  is_active: true,
};

const detail: JobDetail = {
  ...summary,
  description_html: '<p>Build useful software.</p>',
  description_truncated: false,
};

afterEach(cleanup);

describe('JobDetailPanel', () => {
  it('keeps summary context and close control visible while loading', () => {
    const onClose = vi.fn();
    render(
      <JobDetailPanel
        job={summary}
        detail={null}
        isLoading
        error={null}
        isUnavailable={false}
        onRetry={vi.fn()}
        onClose={onClose}
        isAuthenticated={false}
        onRequireAuthForApply={vi.fn()}
      />
    );

    expect(screen.getByRole('heading', { name: 'Software Intern' })).toBeInTheDocument();
    expect(screen.getByText('Loading job description...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Apply Now' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Close job details' }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('renders the fetched description', () => {
    render(
      <JobDetailPanel
        job={summary}
        detail={detail}
        isLoading={false}
        error={null}
        isUnavailable={false}
        onRetry={vi.fn()}
        onClose={vi.fn()}
        isAuthenticated={false}
        onRequireAuthForApply={vi.fn()}
      />
    );

    expect(screen.getByText('Build useful software.')).toBeInTheDocument();
  });

  it('provides retry after a failed detail request', () => {
    const onRetry = vi.fn();
    render(
      <JobDetailPanel
        job={summary}
        detail={null}
        isLoading={false}
        error="Unable to load this job."
        isUnavailable={false}
        onRetry={onRetry}
        onClose={vi.fn()}
        isAuthenticated={false}
        onRequireAuthForApply={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalledOnce();
    expect(screen.getByRole('button', { name: 'Apply Now' })).toBeInTheDocument();
  });

  it('hides apply controls when the job is no longer available', () => {
    render(
      <JobDetailPanel
        job={summary}
        detail={null}
        isLoading={false}
        error="This job is no longer available."
        isUnavailable
        onRetry={vi.fn()}
        onClose={vi.fn()}
        isAuthenticated={false}
        onRequireAuthForApply={vi.fn()}
      />
    );

    expect(screen.queryByRole('button', { name: 'Apply Now' })).not.toBeInTheDocument();
  });
});
