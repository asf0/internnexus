'use server';

import { buildJobFilterParams } from '@/lib/job-filters';
import { fetchCompanies } from '@/lib/api';
import { BackendError, requestBackend } from '@/lib/api.server';
import { ClickResponseSchema, JobListResponseSchema } from '@/lib/schemas';
import type { JobFilters, JobListResponse } from '@/lib/types';

export interface ClickResponse {
  apply_url: string;
  job_id: string;
}

export interface ClickError {
  error: string;
}

/**
 * Lazy-loaded company filter options.
 *
 * The catalogue has ~9k distinct companies (~124 KB of names). Shipping that
 * array in the homepage RSC payload on every render cost more than it saved,
 * so the filter panel requests it only when it is opened. The underlying
 * `fetchCompanies` request is still cached for an hour.
 */
export async function fetchCompanyFilterOptions(): Promise<string[]> {
  try {
    return await fetchCompanies();
  } catch {
    return [];
  }
}

/**
 * Track a job click and get the apply URL with UTM params.
 * Works for both authenticated and anonymous users.
 */
export async function trackJobClick(
  jobId: string,
  utmData?: { utm_medium?: string; utm_campaign?: string }
): Promise<ClickResponse | ClickError> {
  try {
    const result = await requestBackend(
      `/jobs/${jobId}/click`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(utmData || {}),
      },
      undefined,
      { auth: 'optional' }
    );

    if (result.failure) {
      if (result.failure.status === 404) {
        return { error: 'Job not found' };
      }
      return { error: 'Failed to track click' };
    }

    return ClickResponseSchema.parse(result.data);
  } catch {
    return { error: 'Failed to track click' };
  }
}

export type JobPageResult =
  | { readonly ok: true; readonly data: JobListResponse }
  | { readonly ok: false; readonly error: string };

export async function fetchJobPage(filters: JobFilters): Promise<JobPageResult> {
  try {
    const params = buildJobFilterParams(filters);

    const result = await requestBackend(
      `/jobs?${params.toString()}`,
      { cache: 'no-store' },
      JobListResponseSchema,
      { auth: filters.saved_only === '1' ? 'required' : 'optional' }
    );
    if (result.failure) {
      const error =
        result.failure.status === 401
          ? 'Session expired. Please sign in again.'
          : result.failure.message;
      return { ok: false, error };
    }
    return { ok: true, data: result.data };
  } catch (error) {
    if (error instanceof BackendError) {
      if (error.status === 401) {
        return { ok: false, error: 'Session expired. Please sign in again.' };
      }
      return { ok: false, error: error.message };
    }
    return {
      ok: false,
      error: 'Unable to load more jobs. Check your connection and try again.',
    };
  }
}
