'use server';

import {
  AdminUserSchema,
  CreateUserResponseSchema,
  CurrentAdminInfoSchema,
  PaginatedResponseSchema,
  ResetPasswordResponseSchema,
  UserClickSchema,
} from '@/lib/schemas';
import { fetchAdminEndpoint, fetchAdminText } from '@/lib/admin-api';
import type { AdminUser, PaginatedResponse, UserClick, UsersListParams } from './types';

function buildUsersQueryParams(params: UsersListParams): URLSearchParams {
  const searchParams = new URLSearchParams();
  searchParams.set('page', String(params.page || 1));
  searchParams.set('page_size', String(params.pageSize || 20));

  if (params.search) searchParams.set('search', params.search);
  if (params.isAdmin !== undefined) searchParams.set('is_admin', String(params.isAdmin));
  if (params.sortBy) {
    searchParams.set('sort_by', params.sortBy);
    searchParams.set('sort_order', params.sortOrder || 'desc');
  }

  return searchParams;
}

export async function fetchUsers(params: UsersListParams = {}) {
  return fetchAdminEndpoint<PaginatedResponse<AdminUser>>(
    `/admin/users?${buildUsersQueryParams(params).toString()}`,
    { cache: 'no-store' },
    PaginatedResponseSchema(AdminUserSchema),
    'Failed to fetch users'
  );
}

export async function fetchUser(userId: string) {
  return fetchAdminEndpoint<AdminUser>(
    `/admin/users/${userId}`,
    { cache: 'no-store' },
    AdminUserSchema,
    'Failed to fetch user'
  );
}

export async function grantAdmin(userId: string, role: 'admin' | 'super_admin', notes?: string) {
  return fetchAdminEndpoint<unknown>(
    `/admin/users/${userId}/grant-admin`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role, notes }),
    },
    undefined,
    'Failed to grant admin access'
  );
}

export async function revokeAdmin(userId: string): Promise<{ success: boolean; error?: string }> {
  const result = await fetchAdminEndpoint<unknown>(
    `/admin/users/${userId}/revoke-admin`,
    { method: 'DELETE' },
    undefined,
    'Failed to revoke admin access'
  );
  if ('error' in result) return { success: false, error: result.error };
  return { success: true };
}

export async function deactivateUser(
  userId: string
): Promise<{ success: boolean; error?: string }> {
  const result = await fetchAdminEndpoint<unknown>(
    `/admin/users/${userId}/deactivate`,
    { method: 'POST' },
    undefined,
    'Failed to deactivate user'
  );
  if ('error' in result) return { success: false, error: result.error };
  return { success: true };
}

export async function reactivateUser(
  userId: string
): Promise<{ success: boolean; error?: string }> {
  const result = await fetchAdminEndpoint<unknown>(
    `/admin/users/${userId}/reactivate`,
    { method: 'POST' },
    undefined,
    'Failed to reactivate user'
  );
  if ('error' in result) return { success: false, error: result.error };
  return { success: true };
}

export async function fetchCurrentAdmin() {
  return fetchAdminEndpoint<{ id: string; role: 'admin' | 'super_admin' }>(
    '/admin/me',
    { cache: 'no-store' },
    CurrentAdminInfoSchema,
    'Failed to fetch admin info'
  );
}

export async function createUser(
  email: string,
  password: string,
  name?: string
): Promise<{ data?: AdminUser; error?: string }> {
  return fetchAdminEndpoint<AdminUser>(
    '/admin/users',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name }),
    },
    CreateUserResponseSchema,
    'Failed to create user'
  );
}

export async function deleteUser(userId: string): Promise<{ success: boolean; error?: string }> {
  const result = await fetchAdminEndpoint<unknown>(
    `/admin/users/${userId}/hard`,
    { method: 'DELETE' },
    undefined,
    'Failed to delete user'
  );
  if ('error' in result) return { success: false, error: result.error };
  return { success: true };
}

export async function resetUserPassword(
  userId: string
): Promise<{ success?: boolean; error?: string; message?: string }> {
  const result = await fetchAdminEndpoint<{ message: string }>(
    `/admin/users/${userId}/reset-password`,
    { method: 'POST' },
    ResetPasswordResponseSchema,
    'Failed to reset password'
  );
  if ('error' in result) return result;
  return { success: true, message: result.data.message };
}

export async function getUserClicks(
  userId: string,
  page?: number,
  pageSize?: number
): Promise<{ data?: PaginatedResponse<UserClick>; error?: string }> {
  const searchParams = new URLSearchParams();
  searchParams.set('page', String(page || 1));
  searchParams.set('page_size', String(pageSize || 20));

  return fetchAdminEndpoint<PaginatedResponse<UserClick>>(
    `/admin/users/${userId}/clicks?${searchParams.toString()}`,
    { cache: 'no-store' },
    PaginatedResponseSchema(UserClickSchema),
    'Failed to fetch user clicks'
  );
}

export async function updateUserNotes(
  userId: string,
  notes: string | null
): Promise<{ success?: boolean; error?: string }> {
  const result = await fetchAdminEndpoint<unknown>(
    `/admin/users/${userId}/notes`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    },
    undefined,
    'Failed to update notes'
  );
  if ('error' in result) return result;
  return { success: true };
}

export async function exportUsers(): Promise<{ data?: string; error?: string }> {
  return fetchAdminText('/admin/users/export', 'Failed to export users');
}
