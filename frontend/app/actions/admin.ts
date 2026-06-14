'use server';

import {
  AdminJobSchema,
  AdminUserSchema,
  BulkActionResponseSchema,
  ClickResponseSchema,
  CreateJobResponseSchema,
  CreateUserResponseSchema,
  CurrentAdminInfoSchema,
  DayClickStatsSchema,
  PaginatedResponseSchema,
  ResetPasswordResponseSchema,
  UserClickSchema,
} from '@/lib/schemas';
import { fetchAdminEndpoint, fetchAdminText } from '@/lib/admin-api';

// ============================================================================
// Types
// ============================================================================

export interface AdminJob {
  id: string;
  source: string;
  title: string;
  company: string;
  location: string;
  city: string | null;
  state: string | null;
  country: string | null;
  apply_url: string;
  description_text: string;
  job_category: string | null;
  job_type: string | null;
  work_mode: string | null;
  posted_at: string | null;
  is_active: boolean;
  click_count: number;
  created_at: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  name: string | null;
  is_active: boolean;
  created_at: string;
  has_password: boolean;
  admin_role: string | null;
  provider: string | null;
  notes: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages?: number;
}

export interface JobsListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  company?: string;
  category?: string;
  isActive?: boolean;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface UsersListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  isAdmin?: boolean;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface UserClick {
  id: string;
  job_id: string;
  job_title: string;
  company: string;
  apply_url: string;
  clicked_at: string;
  utm_source: string;
  utm_medium: string | null;
  utm_campaign: string | null;
}

export interface CreateJobRequest {
  title: string;
  company: string;
  location: string;
  apply_url: string;
  description_text: string;
  job_category?: string;
  job_type?: string;
  work_mode?: string;
  posted_at?: string;
}

export interface ClicksByUser {
  user_id: string | null;
  email: string | null;
  name: string | null;
  click_count: number;
}

export interface HourlyClicks {
  hour: number;
  clicks: number;
}

export interface TopJobByClicks {
  job_id: string;
  title: string;
  company: string;
  apply_url: string | null;
  click_count: number;
}

export interface DayClickStats {
  date: string;
  total_clicks: number;
  unique_jobs: number;
  unique_users: number;
  anonymous_clicks: number;
  clicks_by_hour: HourlyClicks[];
  top_jobs: TopJobByClicks[];
}

// ============================================================================
// Jobs API
// ============================================================================

function buildJobsQueryParams(params: JobsListParams): URLSearchParams {
  const searchParams = new URLSearchParams();
  searchParams.set('page', String(params.page || 1));
  searchParams.set('page_size', String(params.pageSize || 20));

  if (params.search) searchParams.set('search', params.search);
  if (params.company) searchParams.set('company', params.company);
  if (params.category) searchParams.set('category', params.category);
  if (params.isActive !== undefined) searchParams.set('is_active', String(params.isActive));
  if (params.sortBy) {
    searchParams.set('sort_by', params.sortBy);
    searchParams.set('sort_order', params.sortOrder || 'desc');
  }

  return searchParams;
}

export async function fetchJobs(params: JobsListParams = {}) {
  return fetchAdminEndpoint<PaginatedResponse<AdminJob>>(
    `/admin/jobs?${buildJobsQueryParams(params).toString()}`,
    { cache: 'no-store' },
    PaginatedResponseSchema(AdminJobSchema),
    'Failed to fetch jobs'
  );
}

export async function fetchJob(jobId: string) {
  return fetchAdminEndpoint<AdminJob>(
    `/admin/jobs/${jobId}`,
    { cache: 'no-store' },
    AdminJobSchema,
    'Failed to fetch job'
  );
}

export async function updateJob(
  jobId: string,
  data: Record<string, unknown>
): Promise<{ data?: AdminJob; error?: string }> {
  return fetchAdminEndpoint<AdminJob>(
    `/admin/jobs/${jobId}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    },
    AdminJobSchema,
    'Failed to update job'
  );
}

export async function deactivateJob(jobId: string): Promise<{ success: boolean; error?: string }> {
  const result = await fetchAdminEndpoint<unknown>(
    `/admin/jobs/${jobId}`,
    { method: 'DELETE' },
    undefined,
    'Failed to deactivate job'
  );
  if ('error' in result) return { success: false, error: result.error };
  return { success: true };
}

export async function createJob(
  jobData: CreateJobRequest
): Promise<{ data?: AdminJob; error?: string }> {
  return fetchAdminEndpoint<AdminJob>(
    '/admin/jobs',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(jobData),
    },
    CreateJobResponseSchema,
    'Failed to create job'
  );
}

export async function hardDeleteJob(jobId: string): Promise<{ success: boolean; error?: string }> {
  const result = await fetchAdminEndpoint<unknown>(
    `/admin/jobs/${jobId}/hard`,
    { method: 'DELETE' },
    undefined,
    'Failed to delete job'
  );
  if ('error' in result) return { success: false, error: result.error };
  return { success: true };
}

export async function bulkJobAction(
  jobIds: string[],
  action: 'activate' | 'deactivate' | 'delete'
): Promise<{ data?: { affected: number }; error?: string }> {
  return fetchAdminEndpoint<{ affected: number }>(
    '/admin/jobs/bulk',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_ids: jobIds, action }),
    },
    BulkActionResponseSchema,
    'Failed to perform bulk action'
  );
}

// ============================================================================
// Users API
// ============================================================================

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

// ============================================================================
// Clicks API
// ============================================================================

export async function fetchClicksByUser(
  limit?: number
): Promise<{ data?: ClicksByUser[]; error?: string }> {
  const searchParams = new URLSearchParams();
  if (limit) searchParams.set('limit', String(limit));

  return fetchAdminEndpoint<ClicksByUser[]>(
    `/admin/clicks/by-user?${searchParams.toString()}`,
    { cache: 'no-store' },
    undefined,
    'Failed to fetch clicks by user'
  );
}

export async function fetchDayClickStats(
  date: string
): Promise<{ data?: DayClickStats; error?: string }> {
  return fetchAdminEndpoint<DayClickStats>(
    `/admin/clicks/date/${date}`,
    { cache: 'no-store' },
    DayClickStatsSchema,
    'Failed to fetch day click stats'
  );
}

// Re-export click schema for consumers that need runtime validation.
export { ClickResponseSchema };
