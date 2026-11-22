import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => {
  process.env.AUTH_SECRET = 'test-auth-secret';
  delete process.env.GH_CLIENT_ID;
  delete process.env.GH_CLIENT_SECRET;
  delete process.env.GOOGLE_CLIENT_ID;
  delete process.env.GOOGLE_CLIENT_SECRET;
  return {
    nextAuth: vi.fn((_config: any) => ({
      handlers: {},
      signIn: vi.fn(),
      signOut: vi.fn(),
      auth: vi.fn(),
    })),
    github: vi.fn((options) => ({ id: 'github', options })),
    google: vi.fn((options) => ({ id: 'google', options })),
    credentials: vi.fn((options) => ({ id: 'credentials', options })),
  };
});

vi.mock('next-auth', () => ({ default: mocks.nextAuth }));
vi.mock('next-auth/providers/github', () => ({ default: mocks.github }));
vi.mock('next-auth/providers/google', () => ({ default: mocks.google }));
vi.mock('next-auth/providers/credentials', () => ({ default: mocks.credentials }));

import { getEnabledOAuthProviderNames } from '@/auth';

describe('Auth.js configuration', () => {
  beforeEach(() => vi.unstubAllGlobals());

  it('fails closed for partial provider credentials and enables complete pairs only', () => {
    expect(() => getEnabledOAuthProviderNames({ GH_CLIENT_ID: 'id' })).toThrow(
      /both a client ID and client secret/i
    );
    expect(
      getEnabledOAuthProviderNames({
        GH_CLIENT_ID: 'id',
        GH_CLIENT_SECRET: 'secret',
      })
    ).toEqual(['github']);
  });

  it('registers no OAuth providers when none are configured', () => {
    expect(mocks.github).not.toHaveBeenCalled();
    expect(mocks.google).not.toHaveBeenCalled();
    expect(mocks.credentials).toHaveBeenCalledOnce();
  });

  it('exchanges only provider and access_token with the backend', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ access_token: 'backend-token', user: { id: 'user-1' } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );
    const config = mocks.nextAuth.mock.calls[0]![0];

    await config.callbacks.jwt({
      token: {},
      account: {
        provider: 'github',
        providerAccountId: 'provider-user',
        access_token: 'provider-token',
        refresh_token: 'must-not-leave-frontend',
      },
    });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/oauth/callback'),
      expect.objectContaining({
        body: JSON.stringify({ provider: 'github', access_token: 'provider-token' }),
      })
    );
  });
});
