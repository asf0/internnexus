import { BACKEND_URL } from "./config";
import type { Job, JobListResponse, JobFilters } from "./types";

const API_BASE = typeof window !== 'undefined' ? '/api' : BACKEND_URL;

export async function fetchJobs(
  filters: JobFilters = {}
): Promise<JobListResponse> {
  const params = new URLSearchParams();

  if (filters.page) params.set("page", filters.page.toString());
  if (filters.search) params.set("search", filters.search);
  if (filters.company) params.set("company", filters.company);
  if (filters.location) params.set("location", filters.location);
  if (filters.category) params.set("category", filters.category);
  if (filters.visa_sponsored) params.set("visa_sponsored", filters.visa_sponsored);
  if (filters.f1_friendly) params.set("f1_friendly", filters.f1_friendly);
  if (filters.job_type) params.set("job_type", filters.job_type);
  if (filters.work_mode) params.set("work_mode", filters.work_mode);
  if (filters.posted_within) params.set("posted_within", filters.posted_within);
  if (filters.match_ids) params.set("match_ids", filters.match_ids);

  params.set("page_size", filters.page_size?.toString() || "20");

  const response = await fetch(`${API_BASE}/jobs?${params.toString()}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return { items: [], total: 0, page: 1, page_size: 20 };
  }
  return (await response.json()) as JobListResponse;
}

export async function fetchCompanies(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/jobs/filters/companies`, {
    cache: "no-store"
  });
  if (!response.ok) return [];
  return (await response.json()) as string[];
}

export async function fetchLocations(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/jobs/filters/locations`, {
    cache: "no-store"
  });
  if (!response.ok) return [];
  return (await response.json()) as string[];
}

export async function fetchCategories(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/jobs/filters/categories`, {
    cache: "no-store"
  });
  if (!response.ok) return [];
  return (await response.json()) as string[];
}

export async function fetchJob(id: string): Promise<Job | null> {
  const response = await fetch(`${API_BASE}/jobs/${id}`, {
    cache: "no-store"
  });
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as Job;
}

export async function fetchAllJobIds(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/jobs?page_size=1000`, {
    cache: "no-store"
  });
  if (!response.ok) {
    return [];
  }
  const data = (await response.json()) as JobListResponse;
  return data.items.map((job) => job.id);
}
