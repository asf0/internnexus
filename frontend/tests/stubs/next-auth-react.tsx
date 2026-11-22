import type { ReactNode } from 'react';

export async function signIn() {
  return undefined;
}

export async function signOut() {
  return undefined;
}

export async function getProviders() {
  return null;
}

export function useSession() {
  return { data: null, status: 'unauthenticated', update: async () => undefined };
}

export function SessionProvider({ children }: { readonly children: ReactNode }) {
  return children;
}
