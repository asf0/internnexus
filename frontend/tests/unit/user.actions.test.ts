import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('@/auth', () => ({
  signOut: vi.fn(),
}));

vi.mock('@/lib/api.server', () => ({
  backendFetch: vi.fn(),
  BackendError: class BackendError extends Error {
    constructor(
      public status: number,
      message: string
    ) {
      super(message);
      this.name = 'BackendError';
    }
  },
}));

import { backendFetch, BackendError } from '@/lib/api.server';
import { fetchUserResume } from '@/app/actions/user';

const mockedBackendFetch = vi.mocked(backendFetch);

const sampleResume = {
  id: '1',
  file_name: 'resume.pdf',
  file_hash: 'abc123',
  content_hash: null,
  status: 'ready',
  has_embedding: false,
  embedding_model: null,
  embedding_dim: null,
  last_embedded_at: null,
  embedding_error: null,
  uploaded_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

describe('user actions', () => {
  beforeEach(() => {
    mockedBackendFetch.mockReset();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('fetchUserResume', () => {
    it('returns null data with no error when the backend has no resume', async () => {
      mockedBackendFetch.mockResolvedValue(null);

      const result = await fetchUserResume();

      expect(result).toEqual({ data: null });
      expect(mockedBackendFetch).toHaveBeenCalledWith(
        '/users/me/resume',
        { cache: 'no-store' },
        expect.anything()
      );
      const schema = mockedBackendFetch.mock.calls[0][2]!;
      expect(schema.safeParse(null).success).toBe(true);
      expect(schema.safeParse(sampleResume).success).toBe(true);
    });

    it('returns resume data on success', async () => {
      mockedBackendFetch.mockResolvedValue(sampleResume);

      const result = await fetchUserResume();

      expect(result).toEqual({ data: sampleResume });
    });

    it('returns the backend error message on BackendError', async () => {
      mockedBackendFetch.mockRejectedValue(new BackendError(500, 'Server error'));

      const result = await fetchUserResume();

      expect(result).toEqual({ data: null, error: 'Server error' });
    });

    it('returns a fallback error on unexpected errors', async () => {
      mockedBackendFetch.mockRejectedValue(new Error('boom'));

      const result = await fetchUserResume();

      expect(result).toEqual({ data: null, error: 'Failed to load resume metadata' });
    });
  });
});
