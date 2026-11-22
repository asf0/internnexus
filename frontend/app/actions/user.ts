'use server';

import { logoutUser } from '@/app/actions/auth';
import { BackendError, backendFetch } from '@/lib/api.server';
import { revalidatePath } from 'next/cache';
import {
  HomeStateSchema,
  NotificationItemSchema,
  MCPApiKeySchema,
  CreatedMCPApiKeySchema,
  SavedJobRecordSchema,
  UnreadCountResponseSchema,
  UserProfileSchema,
  UserResumeSchema,
} from '@/lib/schemas';
import type {
  HomeState,
  NotificationItem,
  MCPApiKey,
  CreatedMCPApiKey,
  SavedJobRecord,
  UpdateUserData,
  UserProfile,
  UserResume,
} from '@/lib/types/user';
import { userProfileSchema } from '@/lib/validation';
import { z } from 'zod';

export async function fetchUserProfile(): Promise<UserProfile | null> {
  try {
    return await backendFetch('/users/me', { cache: 'no-store' }, UserProfileSchema);
  } catch (error) {
    if (error instanceof BackendError && error.status === 401) {
      return null;
    }
    if (process.env.NODE_ENV !== 'production') {
      console.error('Error fetching user profile:', error);
    }
    return null;
  }
}

export interface ChangePasswordData {
  current_password: string;
  new_password: string;
}

export async function updateUserProfile(
  data: UpdateUserData
): Promise<{ success: boolean; error?: string; name?: string | null; image?: string | null }> {
  try {
    const parsed = userProfileSchema.safeParse(data);
    if (!parsed.success) {
      return { success: false, error: parsed.error.issues[0]?.message || 'Invalid profile data' };
    }

    const updatedUser = await backendFetch(
      '/users/me',
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed.data),
      },
      UserProfileSchema
    );

    revalidatePath('/');
    revalidatePath('/settings');
    return { success: true, name: updatedUser.name ?? null, image: updatedUser.image ?? null };
  } catch (error) {
    const message = error instanceof BackendError ? error.message : 'An unexpected error occurred';
    if (process.env.NODE_ENV !== 'production') {
      console.error('Error updating user profile:', error);
    }
    return { success: false, error: message };
  }
}

export async function changePassword(
  data: ChangePasswordData
): Promise<{ success: boolean; error?: string }> {
  try {
    await backendFetch('/users/me/password', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const logoutResult = await logoutUser();
    return logoutResult.success ? { success: true } : { success: false, error: logoutResult.error };
  } catch (error) {
    const message = error instanceof BackendError ? error.message : 'An unexpected error occurred';
    if (process.env.NODE_ENV !== 'production') {
      console.error('Error changing password:', error);
    }
    return { success: false, error: message };
  }
}

export async function deleteAccount(): Promise<{ success: boolean; error?: string }> {
  try {
    await backendFetch('/users/me', { method: 'DELETE' });
    const logoutResult = await logoutUser();
    return logoutResult.success ? { success: true } : { success: false, error: logoutResult.error };
  } catch (error) {
    const message = error instanceof BackendError ? error.message : 'An unexpected error occurred';
    if (process.env.NODE_ENV !== 'production') {
      console.error('Error deleting account:', error);
    }
    return { success: false, error: message };
  }
}

// Backward compatibility alias
export const getUserProfile = fetchUserProfile;

export interface FetchUserResumeResult {
  data: UserResume | null;
  error?: string;
}

export async function fetchUserResume(): Promise<FetchUserResumeResult> {
  try {
    const resume = await backendFetch(
      '/users/me/resume',
      { cache: 'no-store' },
      UserResumeSchema.nullable()
    );
    return { data: resume };
  } catch (error) {
    const message =
      error instanceof BackendError ? error.message : 'Failed to load resume metadata';
    if (process.env.NODE_ENV !== 'production') {
      console.error('Error fetching resume metadata:', error);
    }
    return { data: null, error: message };
  }
}

export async function uploadUserResume(
  file: File
): Promise<{ success: boolean; data?: UserResume; error?: string }> {
  try {
    const body = new FormData();
    body.append('file', file, file.name);
    const resume = await backendFetch(
      '/users/me/resume',
      { method: 'POST', body },
      UserResumeSchema
    );
    revalidatePath('/profile');
    return { success: true, data: resume };
  } catch (error) {
    const message = error instanceof BackendError ? error.message : 'Failed to upload resume';
    return { success: false, error: message };
  }
}

export async function deleteUserResume(): Promise<{ success: boolean; error?: string }> {
  try {
    await backendFetch('/users/me/resume', { method: 'DELETE' });
    revalidatePath('/profile');
    return { success: true };
  } catch (error) {
    const message = error instanceof BackendError ? error.message : 'Failed to delete resume';
    return { success: false, error: message };
  }
}

export async function fetchNotifications(): Promise<NotificationItem[]> {
  try {
    return await backendFetch(
      '/users/me/notifications',
      { cache: 'no-store' },
      z.array(NotificationItemSchema)
    );
  } catch {
    return [];
  }
}

export async function fetchUnreadNotificationCount(): Promise<number> {
  try {
    const data = await backendFetch(
      '/users/me/notifications/unread-count',
      { cache: 'no-store' },
      UnreadCountResponseSchema
    );
    return data.unread_count || 0;
  } catch {
    return 0;
  }
}

export async function markNotificationRead(
  notificationId: string
): Promise<{ success: boolean; error?: string }> {
  try {
    await backendFetch(`/users/me/notifications/${notificationId}/read`, { method: 'PATCH' });
    revalidatePath('/profile');
    return { success: true };
  } catch (error) {
    const message = error instanceof BackendError ? error.message : 'Failed to update notification';
    return { success: false, error: message };
  }
}

export async function markAllNotificationsRead(): Promise<{ success: boolean; error?: string }> {
  try {
    await backendFetch('/users/me/notifications/read-all', { method: 'PATCH' });
    revalidatePath('/profile');
    return { success: true };
  } catch (error) {
    const message =
      error instanceof BackendError ? error.message : 'Failed to update notifications';
    return { success: false, error: message };
  }
}

export async function deleteNotification(
  notificationId: string
): Promise<{ success: boolean; error?: string }> {
  try {
    await backendFetch(`/users/me/notifications/${notificationId}`, { method: 'DELETE' });
    revalidatePath('/profile');
    return { success: true };
  } catch (error) {
    const message = error instanceof BackendError ? error.message : 'Failed to delete notification';
    return { success: false, error: message };
  }
}

export async function clearAllNotifications(): Promise<{
  success: boolean;
  error?: string;
}> {
  try {
    await backendFetch('/users/me/notifications', { method: 'DELETE' });
    revalidatePath('/profile');
    return { success: true };
  } catch (error) {
    const message = error instanceof BackendError ? error.message : 'Failed to clear notifications';
    return { success: false, error: message };
  }
}

export async function fetchSavedJobIds(): Promise<string[]> {
  try {
    return await backendFetch(
      '/users/me/saved-jobs/ids',
      { cache: 'no-store' },
      z.array(z.string())
    );
  } catch {
    return [];
  }
}

export async function fetchAppliedJobIds(): Promise<string[]> {
  try {
    return await backendFetch(
      '/users/me/applied-jobs/ids',
      { cache: 'no-store' },
      z.array(z.string())
    );
  } catch {
    return [];
  }
}

/**
 * Homepage bootstrap for a signed-in user: unread count, saved ids, and applied
 * ids in one request. Three separate endpoints would authenticate three times.
 */
export async function fetchHomeState(): Promise<HomeState> {
  try {
    return await backendFetch('/users/me/home-state', { cache: 'no-store' }, HomeStateSchema);
  } catch {
    return { unread_count: 0, saved_job_ids: [], applied_job_ids: [] };
  }
}

export async function fetchSavedJobs(): Promise<SavedJobRecord[]> {
  try {
    return await backendFetch(
      '/users/me/saved-jobs',
      { cache: 'no-store' },
      z.array(SavedJobRecordSchema)
    );
  } catch {
    return [];
  }
}

export async function saveJob(jobId: string): Promise<{ success: boolean; error?: string }> {
  try {
    await backendFetch(`/users/me/saved-jobs/${jobId}`, { method: 'POST' });
    revalidatePath('/profile');
    return { success: true };
  } catch (error) {
    const message = error instanceof BackendError ? error.message : 'Failed to save job';
    return { success: false, error: message };
  }
}

export async function unsaveJob(jobId: string): Promise<{ success: boolean; error?: string }> {
  try {
    await backendFetch(`/users/me/saved-jobs/${jobId}`, { method: 'DELETE' });
    revalidatePath('/profile');
    return { success: true };
  } catch (error) {
    const message = error instanceof BackendError ? error.message : 'Failed to unsave job';
    return { success: false, error: message };
  }
}

export async function markApplied(jobId: string): Promise<{ success: boolean; error?: string }> {
  try {
    await backendFetch(`/users/me/applied-jobs/${jobId}`, { method: 'POST' });
    revalidatePath('/profile');
    return { success: true };
  } catch (error) {
    const message = error instanceof BackendError ? error.message : 'Failed to mark applied';
    return { success: false, error: message };
  }
}

export async function unmarkApplied(jobId: string): Promise<{ success: boolean; error?: string }> {
  try {
    await backendFetch(`/users/me/applied-jobs/${jobId}`, { method: 'DELETE' });
    revalidatePath('/profile');
    return { success: true };
  } catch (error) {
    const message = error instanceof BackendError ? error.message : 'Failed to unmark applied';
    return { success: false, error: message };
  }
}

export async function fetchMCPApiKeys(): Promise<MCPApiKey[]> {
  try {
    return await backendFetch(
      '/users/me/mcp-keys',
      { cache: 'no-store' },
      z.array(MCPApiKeySchema)
    );
  } catch {
    return [];
  }
}

export async function createMCPApiKey(
  name: string,
  expiresInDays: number
): Promise<{ success: boolean; data?: CreatedMCPApiKey; error?: string }> {
  try {
    const data = await backendFetch(
      '/users/me/mcp-keys',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, expires_in_days: expiresInDays }),
      },
      CreatedMCPApiKeySchema
    );
    revalidatePath('/settings');
    return { success: true, data };
  } catch (error) {
    return {
      success: false,
      error: error instanceof BackendError ? error.message : 'Failed to create key',
    };
  }
}

export async function revokeMCPApiKey(
  keyId: string
): Promise<{ success: boolean; error?: string }> {
  try {
    await backendFetch(`/users/me/mcp-keys/${keyId}`, { method: 'DELETE' });
    revalidatePath('/settings');
    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: error instanceof BackendError ? error.message : 'Failed to revoke key',
    };
  }
}
