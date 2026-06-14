'use server';

import {
  BackendError,
  backendFetch,
  createAuthHeaders,
  requireBackendToken,
} from '@/lib/api.server';
import { BACKEND_URL } from '@/lib/config';
import { ClickResponseSchema, JobListResponseSchema } from '@/lib/schemas';
import type { JobListResponse } from '@/lib/types';

export interface ClickResponse {
  apply_url: string;
  job_id: string;
}

export interface ClickError {
  error: string;
}

/**
 * Track a job click and get the apply URL with UTM params.
 * Works for both authenticated and anonymous users.
 */
export async function trackJobClick(
  jobId: string,
  utmData?: { utm_medium?: string; utm_campaign?: string }
): Promise<ClickResponse | ClickError> {
  let token: string | undefined;
  try {
    token = await requireBackendToken();
  } catch {
    token = undefined;
  }

  try {
    const response = await fetch(`${BACKEND_URL}/jobs/${jobId}/click`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && createAuthHeaders(token)),
      },
      body: JSON.stringify(utmData || {}),
    });

    if (!response.ok) {
      if (response.status === 404) {
        return { error: 'Job not found' };
      }
      return { error: 'Failed to track click' };
    }

    return ClickResponseSchema.parse(await response.json());
  } catch {
    return { error: 'Failed to track click' };
  }
}

interface MatchedJobsFilters {
  page?: number;
  page_size?: number;
  search?: string;
  company?: string;
  location?: string;
  category?: string;
  job_type?: string;
  work_mode?: string;
  posted_within?: string;
  match_ids?: string;
}

export async function fetchMatchedJobs(
  filters: MatchedJobsFilters
): Promise<JobListResponse | { error: string }> {
  try {
    const params = new URLSearchParams();

    if (filters.page) params.set('page', filters.page.toString());
    if (filters.search) params.set('search', filters.search);
    if (filters.company) params.set('company', filters.company);
    if (filters.location) params.set('location', filters.location);
    if (filters.category) params.set('category', filters.category);
    if (filters.job_type) params.set('job_type', filters.job_type);
    if (filters.work_mode) params.set('work_mode', filters.work_mode);
    if (filters.posted_within) params.set('posted_within', filters.posted_within);
    if (filters.match_ids) params.set('match_ids', filters.match_ids);

    params.set('page_size', filters.page_size?.toString() || '20');

    return await backendFetch(
      `/jobs?${params.toString()}`,
      { cache: 'no-store' },
      JobListResponseSchema
    );
  } catch (error) {
    if (error instanceof BackendError) {
      if (error.status === 401) {
        return { error: 'Session expired. Please sign in again.' };
      }
      return { error: error.message };
    }
    if (process.env.NODE_ENV !== 'production') {
      console.error('Error fetching matched jobs:', error);
    }
    return { items: [], total: 0, page: 1, page_size: 20 };
  }
}
