import { z } from 'zod';
import 'server-only';
import { BACKEND_URL } from './config';
import { createOptionalAuthHeaders } from './http';
import {
  JobDetailSchema,
  JobListResponseSchema,
  LocationItemSchema,
  SitemapJobListResponseSchema,
} from './schemas';
import type { JobDetail, JobFilters, JobListResponse, LocationItem } from './types/job';
import { buildJobFilterParams } from './job-filters';

export { buildJobFilterParams } from './job-filters';

export type SitemapJobListResponse = z.infer<typeof SitemapJobListResponseSchema>;

const API_BASE = BACKEND_URL;

export async function fetchJobs(
  filters: JobFilters = {},
  backendToken?: string
): Promise<JobListResponse> {
  // Deliberately no-store: arbitrary search/filter values make the URL space
  // unbounded, and Next's on-disk fetch cache has no size or entry limit. The
  // backend already caches this response for five minutes in a bounded
  // (maxsize=1000) in-memory cache, so repeated renders still avoid the DB.
  const response = await fetch(`${API_BASE}/jobs?${buildJobFilterParams(filters).toString()}`, {
    cache: 'no-store',
    headers: createOptionalAuthHeaders(backendToken),
  });
  if (!response.ok) {
    throw new Error(`Unable to load jobs (${response.status})`);
  }
  return JobListResponseSchema.parse(await response.json());
}

// Facet lists take no arguments and carry no auth, so one cached copy is
// correct for every visitor. They shift about as often as the ingestion
// pipeline runs, which is far less than once per render.
const FACET_REVALIDATE_SECONDS = 3600;

export async function fetchCompanies(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/jobs/filters/companies`, {
    next: { revalidate: FACET_REVALIDATE_SECONDS },
  });
  if (!response.ok) return [];
  return z.array(z.string()).parse(await response.json());
}

export async function fetchLocations(
  filters: JobFilters = {},
  backendToken?: string
): Promise<LocationItem[]> {
  const params = buildJobFilterParams(filters);
  params.delete('page');
  params.delete('page_size');

  const response = await fetch(`${API_BASE}/jobs/filters/locations?${params.toString()}`, {
    cache: 'no-store',
    headers: createOptionalAuthHeaders(backendToken),
  });
  if (!response.ok) return [];
  return z.array(LocationItemSchema).parse(await response.json());
}

export async function fetchCategories(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/jobs/filters/categories`, {
    next: { revalidate: FACET_REVALIDATE_SECONDS },
  });
  if (!response.ok) return [];
  return z.array(z.string()).parse(await response.json());
}

export async function fetchJob(id: string, signal?: AbortSignal): Promise<JobDetail | null> {
  const response = await fetch(`${API_BASE}/jobs/${id}`, {
    cache: 'no-store',
    signal,
  });
  // Any 4xx (not just a clean 404) means this URL can never resolve — e.g. a
  // malformed/legacy job id fails FastAPI's UUID path validation with a 422.
  // Treat all of these as "not found" so callers render a real not-found
  // state instead of a generic error, and the App Router page can call
  // notFound() to emit a correct HTTP 404 status.
  if (response.status >= 400 && response.status < 500) return null;
  if (!response.ok) throw new Error(`Unable to load job details (${response.status})`);
  return JobDetailSchema.parse(await response.json());
}

/**
 * Fetch a slice of active job ids for sitemap generation.
 *
 * Deliberately not `cache: 'no-store'`: the sitemap route relies on ISR
 * (`export const revalidate`), and an uncached fetch would force it dynamic
 * again, re-running this on every crawler hit.
 *
 * Throws on failure rather than returning a partial slice. A throw makes ISR
 * keep serving the last good sitemap; silently returning what arrived before
 * an error would publish a permanently truncated one.
 */
export async function fetchSitemapJobIds({
  limit,
  offset = 0,
}: {
  limit: number;
  offset?: number;
}): Promise<SitemapJobListResponse> {
  const params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
  const response = await fetch(`${API_BASE}/jobs/sitemap-ids?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Unable to load sitemap job ids (${response.status})`);
  }
  return SitemapJobListResponseSchema.parse(await response.json());
}

/**
 * Fetch a small slice of jobs related to one job for the detail page's link
 * modules. Deliberately no-store: a per-job Next cache entry created ~900k
 * files / 7.8 GB on the production frontend in four days. The backend caches
 * this response for 15 minutes, and the query is index-backed. All 4xx (404
 * unknown, 410 deactivated) mean "nothing to show" rather than an error: the
 * module simply renders empty.
 */
export async function fetchRelatedJobs(jobId: string): Promise<JobListResponse['items']> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/related`, {
    cache: 'no-store',
  });
  if (response.status >= 400 && response.status < 500) return [];
  if (!response.ok) return [];
  const body = JobListResponseSchema.parse(await response.json());
  return body.items;
}
