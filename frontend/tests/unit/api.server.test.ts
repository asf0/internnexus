import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { z } from 'zod';
import {
  createAuthHeaders,
  requireBackendToken,
  parseBackendError,
  backendFetch,
  BackendError,
} from '@/lib/api.server';

vi.mock('@/lib/auth.server', () => ({
  getBackendToken: vi.fn(),
}));

import { getBackendToken } from '@/lib/auth.server';

const mockedGetBackendToken = vi.mocked(getBackendToken);

describe('api.server helpers', () => {
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

  describe('createAuthHeaders', () => {
    it('builds Bearer headers and merges extra headers', () => {
      expect(createAuthHeaders('token123')).toEqual({ Authorization: 'Bearer token123' });
      expect(createAuthHeaders('token123', { 'X-Custom': 'value' })).toEqual({
        Authorization: 'Bearer token123',
        'X-Custom': 'value',
      });
    });
  });

  describe('requireBackendToken', () => {
    it('returns the token when present', async () => {
      mockedGetBackendToken.mockResolvedValue('valid-token');
      await expect(requireBackendToken()).resolves.toBe('valid-token');
    });

    it('throws a BackendError when token is missing', async () => {
      mockedGetBackendToken.mockResolvedValue(undefined);
      await expect(requireBackendToken()).rejects.toThrow(BackendError);
      await expect(requireBackendToken()).rejects.toMatchObject({
        status: 401,
        message: 'Not authenticated',
      });
    });
  });

  describe('parseBackendError', () => {
    it('extracts detail from a JSON error body', async () => {
      const response = new Response(JSON.stringify({ detail: 'Bad request' }), { status: 400 });
      await expect(parseBackendError(response)).resolves.toBe('Bad request');
    });

    it('falls back to status text when body is not JSON', async () => {
      const response = new Response('plain text', { status: 503 });
      await expect(parseBackendError(response)).resolves.toBe('Request failed (503)');
    });
  });

  describe('backendFetch', () => {
    it('returns parsed JSON on success', async () => {
      mockedGetBackendToken.mockResolvedValue('token');
      const data = { id: '1', title: 'Job' };
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve(
            new Response(JSON.stringify(data), {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            })
          )
        )
      );

      const result = await backendFetch<{ id: string; title: string }>('/jobs/1');
      expect(result).toEqual(data);
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/jobs/1'),
        expect.objectContaining({
          headers: { Authorization: 'Bearer token' },
          cache: 'no-store',
        })
      );
    });

    it('validates response against a Zod schema', async () => {
      mockedGetBackendToken.mockResolvedValue('token');
      const schema = z.object({ id: z.string() });
      const safeParseSpy = vi.spyOn(schema, 'safeParse');
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve(
            new Response(JSON.stringify({ id: '1' }), {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            })
          )
        )
      );

      await backendFetch('/jobs/1', {}, schema);
      expect(safeParseSpy).toHaveBeenCalledWith({ id: '1' });
    });

    it('throws BackendError on non-ok response', async () => {
      mockedGetBackendToken.mockResolvedValue('token');
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve(new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 }))
        )
      );

      await expect(backendFetch('/jobs/1')).rejects.toThrow(BackendError);
      await expect(backendFetch('/jobs/1')).rejects.toMatchObject({
        status: 404,
        message: 'Not found',
      });
    });

    it('throws BackendError when schema validation fails', async () => {
      mockedGetBackendToken.mockResolvedValue('token');
      const schema = z.object({ id: z.string() });
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

      await expect(backendFetch('/jobs/1', {}, schema)).rejects.toThrow(BackendError);
      await expect(backendFetch('/jobs/1', {}, schema)).rejects.toMatchObject({
        message: 'Invalid response from server',
      });
    });
  });
});
