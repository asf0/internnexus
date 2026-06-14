import { z } from 'zod';
import { BACKEND_URL } from './config';
import { createOptionalAuthHeaders } from './http';
import { JobListResponseSchema, LocationItemSchema, MatchFacetsResponseSchema } from './schemas';
import type { JobFilters, JobListResponse, MatchFacetsResponse } from './types/job';
import type { LocationItem } from './types/job';

const API_BASE = typeof window !== 'undefined' ? '/api' : BACKEND_URL;

function buildJobFilterParams(filters: JobFilters): URLSearchParams {
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
  if (filters.saved_only) params.set('saved_only', filters.saved_only);

  params.set('page_size', filters.page_size?.toString() || '20');

  return params;
}

export async function fetchJobs(
  filters: JobFilters = {},
  backendToken?: string
): Promise<JobListResponse> {
  const response = await fetch(`${API_BASE}/jobs?${buildJobFilterParams(filters).toString()}`, {
    cache: 'no-store',
    headers: createOptionalAuthHeaders(backendToken),
  });
  if (!response.ok) {
    return { items: [], total: 0, page: 1, page_size: 20 };
  }
  return JobListResponseSchema.parse(await response.json());
}

export async function fetchCompanies(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/jobs/filters/companies`, {
    cache: 'no-store',
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
    cache: 'no-store',
  });
  if (!response.ok) return [];
  return z.array(z.string()).parse(await response.json());
}

export async function fetchJob(id: string): Promise<JobListResponse['items'][number] | null> {
  const response = await fetch(`${API_BASE}/jobs/${id}`, {
    cache: 'no-store',
  });
  if (!response.ok) {
    return null;
  }
  return JobListResponseSchema.shape.items.element.parse(await response.json());
}

export async function fetchAllJobIds(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/jobs?page_size=1000`, {
    cache: 'no-store',
  });
  if (!response.ok) {
    return [];
  }
  const data = JobListResponseSchema.parse(await response.json());
  return data.items.map((job) => job.id);
}

export async function fetchMatchFacets(
  sessionId: string,
  filters: JobFilters = {},
  backendToken?: string
): Promise<MatchFacetsResponse | null> {
  const params = new URLSearchParams();

  if (filters.search) params.set('search', filters.search);
  if (filters.company) params.set('company', filters.company);
  if (filters.location) params.set('location', filters.location);
  if (filters.category) params.set('category', filters.category);
  if (filters.job_type) params.set('job_type', filters.job_type);
  if (filters.work_mode) params.set('work_mode', filters.work_mode);
  if (filters.posted_within) params.set('posted_within', filters.posted_within);

  const response = await fetch(`${BACKEND_URL}/match/${sessionId}/facets?${params.toString()}`, {
    cache: 'no-store',
    headers: createOptionalAuthHeaders(backendToken),
  });

  if (!response.ok) return null;
  return MatchFacetsResponseSchema.parse(await response.json());
}
