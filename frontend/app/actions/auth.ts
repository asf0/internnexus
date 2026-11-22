'use server';

import { BackendError, requestBackend } from '@/lib/api.server';
import type { RegisterRequest } from '@/lib/types/auth';

export type LogoutResult = { success: true } | { success: false; error: string };

export async function registerUser(data: RegisterRequest): Promise<{
  success: boolean;
  error?: string;
  errorType?: string;
}> {
  try {
    const result = await requestBackend(
      '/auth/register',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      },
      undefined,
      { auth: 'none' }
    );

    if (result.failure) {
      const detail = (
        result.failure.body as { detail?: { message?: string; error?: string } } | undefined
      )?.detail;
      return {
        success: false,
        error: detail?.message || 'Registration failed. Please try again.',
        errorType: detail?.error,
      };
    }

    return { success: true };
  } catch (error) {
    if (process.env.NODE_ENV !== 'production') {
      console.error('Registration error:', error);
    }
    return { success: false, error: 'An unexpected error occurred. Please try again.' };
  }
}

export async function logoutUser(): Promise<LogoutResult> {
  try {
    const result = await requestBackend('/auth/logout', { method: 'POST' });
    if (result.failure && result.failure.status !== 401) {
      return { success: false, error: result.failure.message || 'Failed to sign out' };
    }
  } catch (error) {
    if (!(error instanceof BackendError && error.status === 401)) {
      return { success: false, error: 'Failed to sign out. Please try again.' };
    }
  }

  const { signOut } = await import('@/auth');
  await signOut({ redirect: false });
  return { success: true };
}
