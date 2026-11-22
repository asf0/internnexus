import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  cookies: vi.fn(),
  decode: vi.fn(),
}));

vi.mock('next/headers', () => ({ cookies: mocks.cookies }));
vi.mock('next-auth/jwt', () => ({ decode: mocks.decode }));

import { getBackendToken } from '@/lib/auth.server';

describe('getBackendToken', () => {
  beforeEach(() => {
    process.env.AUTH_SECRET = 'test-auth-secret';
    mocks.cookies.mockReset();
    mocks.decode.mockReset();
  });

  it('reads the cookie once and returns a typed authenticated result', async () => {
    const get = vi.fn((name: string) =>
      name === 'authjs.session-token' ? { value: 'encrypted-cookie' } : undefined
    );
    mocks.cookies.mockResolvedValue({ get });
    mocks.decode.mockResolvedValue({ backendToken: 'backend-jwt' });

    await expect(getBackendToken()).resolves.toEqual({ ok: true, token: 'backend-jwt' });
    expect(mocks.cookies).toHaveBeenCalledOnce();
    expect(mocks.decode).toHaveBeenCalledOnce();
  });

  it('distinguishes missing and invalid cookies without retrying', async () => {
    mocks.cookies.mockResolvedValueOnce({ get: vi.fn(() => undefined) });
    await expect(getBackendToken()).resolves.toEqual({ ok: false, reason: 'missing' });

    mocks.cookies.mockResolvedValueOnce({ get: vi.fn(() => ({ value: 'bad' })) });
    mocks.decode.mockRejectedValueOnce(new Error('invalid'));
    await expect(getBackendToken()).resolves.toEqual({ ok: false, reason: 'invalid' });
    expect(mocks.cookies).toHaveBeenCalledTimes(2);
    expect(mocks.decode).toHaveBeenCalledOnce();
  });
});
