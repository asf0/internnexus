'use server';

import {
  AdminJobSchema,
  BulkActionResponseSchema,
  CreateJobResponseSchema,
  PaginatedResponseSchema,
} from '@/lib/schemas';
import { fetchAdminEndpoint } from '@/lib/admin-api';
import type { AdminJob, CreateJobRequest, JobsListParams, PaginatedResponse } from './types';

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
