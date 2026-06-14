import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { z } from 'zod';
import { fetchAdminEndpoint, fetchAdminText, fetchAdminData } from '@/lib/admin-api';

vi.mock('@/lib/auth.server', () => ({
  getBackendToken: vi.fn(),
}));

import { getBackendToken } from '@/lib/auth.server';

const mockedGetBackendToken = vi.mocked(getBackendToken);

describe('admin-api', () => {
  beforeEach(() => {
    mockedGetBackendToken.mockReset();
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response('{}', { status: 200 })))
    );
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('fetchAdminEndpoint', () => {
    it('returns data on successful JSON response', async () => {
      mockedGetBackendToken.mockResolvedValue('admin-token');
      const payload = { users: [] };
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve(
            new Response(JSON.stringify(payload), {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            })
          )
        )
      );

      const result = await fetchAdminEndpoint<{ users: unknown[] }>('/admin/users');
      expect(result.data).toEqual(payload);
      expect(result.error).toBeUndefined();
    });

    it('returns a parsed error on non-ok response', async () => {
      mockedGetBackendToken.mockResolvedValue('admin-token');
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve(new Response(JSON.stringify({ detail: 'Forbidden' }), { status: 403 }))
        )
      );

      const result = await fetchAdminEndpoint('/admin/users');
      expect(result.error).toBe('Forbidden');
      expect(result.data).toBeUndefined();
    });

    it('returns fallback error on network failure', async () => {
      mockedGetBackendToken.mockResolvedValue('admin-token');
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.reject(new Error('Network error')))
      );

      const result = await fetchAdminEndpoint(
        '/admin/users',
        {},
        undefined,
        'Admin request failed'
      );
      expect(result.error).toBe('Admin request failed');
    });

    it('returns auth error message when token is missing', async () => {
      mockedGetBackendToken.mockResolvedValue(undefined);

      const result = await fetchAdminEndpoint('/admin/users');
      expect(result.error).toBe('Not authenticated');
    });

    it('returns fallback error when schema validation fails', async () => {
      mockedGetBackendToken.mockResolvedValue('admin-token');
      const schema = z.object({ users: z.array(z.unknown()) });
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve(
            new Response(JSON.stringify({ unexpected: true }), {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            })
          )
        )
      );

      const result = await fetchAdminEndpoint('/admin/users', {}, schema, 'Validation failed');
      expect(result.error).toBe('Validation failed');
    });
  });

  describe('fetchAdminText', () => {
    it('returns text on success', async () => {
      mockedGetBackendToken.mockResolvedValue('admin-token');
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.resolve(new Response('export data', { status: 200 })))
      );

      const result = await fetchAdminText('/admin/export');
      expect(result.data).toBe('export data');
    });

    it('returns a status-based error when the error body has no detail', async () => {
      mockedGetBackendToken.mockResolvedValue('admin-token');
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.resolve(new Response('Server error', { status: 500 })))
      );

      const result = await fetchAdminText('/admin/export', 'Export failed');
      expect(result.error).toBe('Request failed (500)');
    });
  });

  describe('fetchAdminData', () => {
    it('returns parsed data on success', async () => {
      mockedGetBackendToken.mockResolvedValue('admin-token');
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve(
            new Response(JSON.stringify({ count: 5 }), {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            })
          )
        )
      );

      const result = await fetchAdminData<{ count: number }>('/admin/stats');
      expect(result).toEqual({ count: 5 });
    });

    it('returns null on non-ok response', async () => {
      mockedGetBackendToken.mockResolvedValue('admin-token');
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.resolve(new Response('Unauthorized', { status: 401 })))
      );

      const result = await fetchAdminData('/admin/stats');
      expect(result).toBeNull();
    });

    it('returns null when schema validation fails', async () => {
      mockedGetBackendToken.mockResolvedValue('admin-token');
      const schema = z.object({ count: z.number() });
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve(
            new Response(JSON.stringify({ count: 'not a number' }), {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            })
          )
        )
      );

      const result = await fetchAdminData('/admin/stats', schema);
      expect(result).toBeNull();
    });
  });
});
