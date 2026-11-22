import { cookies } from 'next/headers';
import { decode } from 'next-auth/jwt';
import { cache } from 'react';

export type BackendTokenResult =
  | { readonly ok: true; readonly token: string }
  | { readonly ok: false; readonly reason: 'missing' | 'invalid' };

/**
 * Server-side only helper to get the backend JWT token.
 * This token is NEVER exposed to the client - it stays in the HTTP-only cookie.
 * Use this in server actions and API routes to make authenticated requests to the backend.
 */
export const getBackendToken = cache(async function getBackendToken(): Promise<BackendTokenResult> {
  const authSecret = process.env.AUTH_SECRET;
  if (!authSecret) {
    if (process.env.NEXT_PHASE === 'phase-production-build') {
      return { ok: false, reason: 'missing' };
    }
    throw new Error('AUTH_SECRET environment variable is required');
  }

  const cookieStore = await cookies();
  const candidates = [
    '__Secure-authjs.session-token',
    'authjs.session-token',
    'next-auth.session-token',
  ] as const;
  const cookieName = candidates.find((name) => cookieStore.get(name)?.value);
  if (!cookieName) {
    return { ok: false, reason: 'missing' };
  }

  try {
    const decoded = await decode({
      token: cookieStore.get(cookieName)?.value,
      secret: authSecret,
      salt: cookieName,
    });
    return typeof decoded?.backendToken === 'string' && decoded.backendToken
      ? { ok: true, token: decoded.backendToken }
      : { ok: false, reason: 'invalid' };
  } catch {
    return { ok: false, reason: 'invalid' };
  }
});
