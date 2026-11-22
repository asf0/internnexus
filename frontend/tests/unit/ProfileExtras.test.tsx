import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import ProfileExtras from '@/components/profile/ProfileExtras';

vi.mock('@/app/actions/user', () => ({
  deleteUserResume: vi.fn(),
  markAllNotificationsRead: vi.fn(),
  markNotificationRead: vi.fn(),
  uploadUserResume: vi.fn(),
}));

afterEach(() => {
  cleanup();
});

describe('ProfileExtras', () => {
  it('presents resume status without exposing internal hashes or model details', () => {
    render(
      <ProfileExtras
        initialResume={{
          id: 'resume-1',
          file_name: 'resume.pdf',
          file_hash: 'secret-internal-hash',
          content_hash: null,
          status: 'ready',
          has_embedding: true,
          embedding_model: 'internal-model',
          embedding_dim: 1024,
          last_embedded_at: '2026-07-02T00:00:00Z',
          embedding_error: null,
          uploaded_at: '2026-07-01T00:00:00Z',
          updated_at: '2026-07-02T00:00:00Z',
        }}
        initialNotifications={[]}
        initialSavedJobs={[]}
      />
    );

    expect(screen.getByText('Ready for matching')).toBeInTheDocument();
    expect(screen.queryByText(/secret-internal-hash/)).not.toBeInTheDocument();
    expect(screen.queryByText(/internal-model/)).not.toBeInTheDocument();
  });

  it('formats notification types and links to the saved-jobs search', () => {
    render(
      <ProfileExtras
        initialResume={null}
        initialNotifications={[
          {
            id: 'notification-1',
            type: 'resume.updated',
            payload: { message: 'Resume is ready' },
            is_read: false,
            created_at: '2026-07-02T00:00:00Z',
            read_at: null,
          },
        ]}
        initialSavedJobs={[
          {
            id: 'saved-1',
            job_id: 'job-1',
            created_at: '2026-07-02T00:00:00Z',
            job: {
              id: 'job-1',
              source: 'greenhouse',
              title: 'Software Engineer',
              company: 'Example',
              location: 'Remote',
              city: null,
              state: null,
              country: null,
              apply_url: 'https://example.com/apply',
              job_category: null,
              job_type: null,
              work_mode: 'remote',
              posted_at: '2026-07-01T00:00:00Z',
              is_active: true,
            },
          },
        ]}
      />
    );

    expect(screen.getByText('Resume Updated')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'View all saved jobs' })).toHaveAttribute(
      'href',
      '/?saved_only=1'
    );
  });
});
