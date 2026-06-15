import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('@/lib/auth.server', () => ({
  getBackendToken: vi.fn(),
}));

import { getBackendToken } from '@/lib/auth.server';
import { matchResume, matchProfileResume } from '@/app/actions/match';

const mockedGetBackendToken = vi.mocked(getBackendToken);

const validMatchResponse = {
  matches: [],
  total: 0,
  session_id: 'session-1',
  page: 1,
  page_size: 20,
  total_pages: 0,
};

function stubFetch(response: Response): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve(response))
  );
}

function createFormData(fileName = 'resume.pdf'): FormData {
  const formData = new FormData();
  formData.append('resume', new File(['content'], fileName, { type: 'application/pdf' }));
  return formData;
}

describe('match actions', () => {
  beforeEach(() => {
    mockedGetBackendToken.mockReset();
    stubFetch(
      new Response(JSON.stringify(validMatchResponse), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('matchResume', () => {
    it('returns session expired error when no backend token is available', async () => {
      mockedGetBackendToken.mockResolvedValue(undefined);

      const result = await matchResume(createFormData());

      expect(result.error).toBe('Your session has expired. Please sign in again.');
      expect(fetch).not.toHaveBeenCalled();
    });

    it('sends an Authorization header with the FormData body', async () => {
      mockedGetBackendToken.mockResolvedValue('token123');

      await matchResume(createFormData());

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/match'),
        expect.objectContaining({
          method: 'POST',
          headers: { Authorization: 'Bearer token123' },
          body: expect.any(FormData),
        })
      );
    });

    it('returns session expired error on 401 response', async () => {
      mockedGetBackendToken.mockResolvedValue('token123');
      stubFetch(
        new Response(JSON.stringify({ detail: 'Authentication required' }), { status: 401 })
      );

      const result = await matchResume(createFormData());

      expect(result.error).toBe('Your session has expired. Please sign in again.');
    });

    it('returns parsed match response on success', async () => {
      mockedGetBackendToken.mockResolvedValue('token123');

      const result = await matchResume(createFormData());

      expect(result).toEqual(expect.objectContaining(validMatchResponse));
    });
  });

  describe('matchProfileResume', () => {
    it('returns session expired error when no backend token is available', async () => {
      mockedGetBackendToken.mockResolvedValue(undefined);

      const result = await matchProfileResume();

      expect(result.error).toBe('Your session has expired. Please sign in again.');
      expect(fetch).not.toHaveBeenCalled();
    });

    it('sends an Authorization header', async () => {
      mockedGetBackendToken.mockResolvedValue('token123');

      await matchProfileResume();

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/match/profile'),
        expect.objectContaining({
          method: 'POST',
          headers: { Authorization: 'Bearer token123' },
        })
      );
    });

    it('returns session expired error on 401 response', async () => {
      mockedGetBackendToken.mockResolvedValue('token123');
      stubFetch(
        new Response(JSON.stringify({ detail: 'Authentication required' }), { status: 401 })
      );

      const result = await matchProfileResume();

      expect(result.error).toBe('Your session has expired. Please sign in again.');
    });

    it('returns parsed match response on success', async () => {
      mockedGetBackendToken.mockResolvedValue('token123');

      const result = await matchProfileResume();

      expect(result).toEqual(expect.objectContaining(validMatchResponse));
    });
  });
});
