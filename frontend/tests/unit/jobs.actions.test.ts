import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({ requestBackend: vi.fn() }));

vi.mock('@/lib/api.server', () => ({
  requestBackend: mocks.requestBackend,
  BackendError: class BackendError extends Error {
    constructor(
      public status: number,
      message: string
    ) {
      super(message);
    }
  },
}));

import { fetchJobPage } from '@/app/actions/jobs';

describe('fetchJobPage', () => {
  beforeEach(() => mocks.requestBackend.mockReset());

  it('uses optional auth for public load-more pages', async () => {
    const data = { items: [], total: 0, page: 2, page_size: 20 };
    mocks.requestBackend.mockResolvedValue({ data });

    await expect(fetchJobPage({ page: 2 })).resolves.toEqual({ ok: true, data });
    expect(mocks.requestBackend).toHaveBeenCalledWith(
      expect.stringContaining('/jobs?'),
      { cache: 'no-store' },
      expect.anything(),
      { auth: 'optional' }
    );
  });

  it('requires auth for saved jobs and surfaces an expired session', async () => {
    mocks.requestBackend.mockResolvedValue({
      failure: { status: 401, message: 'Not authenticated' },
    });

    await expect(fetchJobPage({ page: 2, saved_only: '1' })).resolves.toEqual({
      ok: false,
      error: 'Session expired. Please sign in again.',
    });
    expect(mocks.requestBackend).toHaveBeenCalledWith(
      expect.any(String),
      expect.anything(),
      expect.anything(),
      { auth: 'required' }
    );
  });
});
