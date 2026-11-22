import NextAuth from 'next-auth';
import GitHub from 'next-auth/providers/github';
import Google from 'next-auth/providers/google';
import Credentials from 'next-auth/providers/credentials';
import type { DefaultSession } from 'next-auth';
import { SESSION_MAX_AGE_SECONDS, SESSION_UPDATE_AGE_SECONDS } from '@/lib/constants';

const backendBaseUrl = process.env.BACKEND_URL;

// Fail fast at runtime when the session secret is missing; without this
// NextAuth only errors on the first sign-in attempt. `next build` runs
// without secrets by design, so the build phase is exempt.
const authSecret = process.env.AUTH_SECRET;
if (!authSecret && process.env.NEXT_PHASE !== 'phase-production-build') {
  throw new Error('AUTH_SECRET environment variable is required');
}

export type OAuthProviderName = 'github' | 'google';

type AuthToken = {
  backendToken?: string;
  id?: string;
  name?: string | null;
  picture?: string | null;
};

type OAuthAccount = {
  access_token?: string | null;
  provider: string;
};

export function getEnabledOAuthProviderNames(
  env: Record<string, string | undefined> = process.env
): OAuthProviderName[] {
  const providers = [
    ['github', env.GH_CLIENT_ID, env.GH_CLIENT_SECRET],
    ['google', env.GOOGLE_CLIENT_ID, env.GOOGLE_CLIENT_SECRET],
  ] as const;

  return providers.flatMap(([name, clientId, clientSecret]) => {
    if (Boolean(clientId) !== Boolean(clientSecret)) {
      throw new Error(`${name} OAuth requires both a client ID and client secret`);
    }
    return clientId && clientSecret ? [name] : [];
  });
}

const enabledOAuthProviders = getEnabledOAuthProviderNames();

function updateSessionToken(
  token: AuthToken,
  session: { name?: string | null; image?: string | null }
) {
  if (session.name !== undefined) token.name = session.name;
  if (session.image !== undefined) token.picture = session.image;
}

async function exchangeOAuthToken(
  account: OAuthAccount
): Promise<{ accessToken: string; userId: string }> {
  if (!account.access_token) {
    throw new Error('Access token is missing from OAuth provider');
  }

  const response = await fetch(`${backendBaseUrl}/auth/oauth/callback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider: account.provider, access_token: account.access_token }),
  });

  if (!response.ok) {
    if (process.env.NODE_ENV !== 'production') {
      console.error('OAuth callback failed:', await response.text());
    }
    throw new Error('Failed to exchange OAuth token');
  }

  const data = await response.json();
  return { accessToken: data.access_token, userId: data.user.id };
}

async function attachOAuthToken(token: AuthToken, account: OAuthAccount): Promise<void> {
  try {
    const { accessToken, userId } = await exchangeOAuthToken(account);
    token.backendToken = accessToken;
    token.id = userId;
  } catch (error) {
    if (process.env.NODE_ENV !== 'production') {
      console.error('OAuth exchange error:', error);
    }
    throw new Error('Unable to establish backend session', { cause: error });
  }
}

// Extend the session type with the backend identity kept in the encrypted Auth.js JWT.
declare module 'next-auth' {
  interface Session {
    user: {
      id?: string;
    } & DefaultSession['user'];
  }

  interface JWT {
    backendToken?: string; // Our backend JWT token
    id?: string;
  }

  interface User {
    backendToken?: string;
  }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  trustHost: true,
  providers: [
    ...(enabledOAuthProviders.includes('github')
      ? [
          GitHub({
            clientId: process.env.GH_CLIENT_ID!,
            clientSecret: process.env.GH_CLIENT_SECRET!,
          }),
        ]
      : []),
    ...(enabledOAuthProviders.includes('google')
      ? [
          Google({
            clientId: process.env.GOOGLE_CLIENT_ID!,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
          }),
        ]
      : []),
    Credentials({
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      authorize: async (credentials) => {
        // Call backend login endpoint
        const email = credentials?.email as string | undefined;
        const password = credentials?.password as string | undefined;

        if (!email || !password) {
          return null;
        }

        try {
          const response = await fetch(`${backendBaseUrl}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail?.message || 'Login failed');
          }

          const data = await response.json();

          return {
            id: data.user.id,
            email: data.user.email,
            name: data.user.name,
            backendToken: data.access_token,
          };
        } catch (error) {
          if (process.env.NODE_ENV !== 'production') {
            console.error('Login error:', error);
          }
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user, account, trigger, session }) {
      // Handle session update (after profile save)
      if (trigger === 'update' && session) {
        updateSessionToken(token, session);
      }

      // Handle OAuth sign-in
      if (account) {
        await attachOAuthToken(token, account);
      }

      // Handle credentials sign-in
      if (user?.backendToken) {
        token.backendToken = user.backendToken;
        token.id = user.id;
      }

      return token;
    },
    async session({ session, token }) {
      // Only expose user ID - backendToken stays in server-side JWT only
      session.user.id = token.id as string;
      session.user.name = (token.name as string) ?? null;
      session.user.email = (token.email as string) ?? null;
      session.user.image = (token.picture as string) ?? null;
      return session;
    },
  },

  session: {
    strategy: 'jwt',
    maxAge: SESSION_MAX_AGE_SECONDS,
    updateAge: SESSION_UPDATE_AGE_SECONDS,
  },
  secret: authSecret,
});
