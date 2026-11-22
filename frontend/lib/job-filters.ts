import { DEFAULT_PAGE_SIZE } from './constants';
import type { JobFilters } from './types/job';

export function buildJobFilterParams(filters: JobFilters): URLSearchParams {
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
  params.set('page_size', filters.page_size?.toString() || DEFAULT_PAGE_SIZE.toString());
  return params;
}
