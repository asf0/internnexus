import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({ requestBackend: vi.fn(), signOut: vi.fn() }));

vi.mock('@/auth', () => ({ signOut: mocks.signOut }));
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

import { logoutUser } from '@/app/actions/auth';

describe('logoutUser', () => {
  beforeEach(() => {
    mocks.requestBackend.mockReset();
    mocks.signOut.mockReset();
  });

  it('revokes the backend session before clearing Auth.js', async () => {
    mocks.requestBackend.mockResolvedValue({ data: undefined });

    await expect(logoutUser()).resolves.toEqual({ success: true });
    expect(mocks.requestBackend).toHaveBeenCalledWith('/auth/logout', { method: 'POST' });
    expect(mocks.signOut).toHaveBeenCalledWith({ redirect: false });
    expect(mocks.requestBackend.mock.invocationCallOrder[0]).toBeLessThan(
      mocks.signOut.mock.invocationCallOrder[0]
    );
  });

  it('does not clear the cookie when revocation fails', async () => {
    mocks.requestBackend.mockResolvedValue({ failure: { status: 503, message: 'Unavailable' } });

    await expect(logoutUser()).resolves.toEqual({ success: false, error: 'Unavailable' });
    expect(mocks.signOut).not.toHaveBeenCalled();
  });

  it('clears an already-invalid session after a backend 401', async () => {
    mocks.requestBackend.mockResolvedValue({ failure: { status: 401, message: 'Invalid' } });

    await expect(logoutUser()).resolves.toEqual({ success: true });
    expect(mocks.signOut).toHaveBeenCalledOnce();
  });
});
