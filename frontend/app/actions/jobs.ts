"use server";

import { getBackendToken } from "@/lib/auth.server";
import { BACKEND_URL } from "@/lib/config";
import type { JobListResponse } from "@/lib/types";

interface MatchedJobsFilters {
  page?: number;
  page_size?: number;
  search?: string;
  company?: string;
  location?: string;
  category?: string;
  visa_sponsored?: string;
  f1_friendly?: string;
  job_type?: string;
  work_mode?: string;
  posted_within?: string;
  match_ids?: string;
}

export async function fetchMatchedJobs(
  filters: MatchedJobsFilters
): Promise<JobListResponse | { error: string }> {
  const backendToken = await getBackendToken();

  if (!backendToken) {
    return { error: "Authentication required" };
  }

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

  try {
    const response = await fetch(`${BACKEND_URL}/jobs?${params.toString()}`, {
      cache: "no-store",
      headers: {
        Authorization: `Bearer ${backendToken}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        return { error: "Session expired. Please sign in again." };
      }
      return { items: [], total: 0, page: 1, page_size: 20 };
    }

    return (await response.json()) as JobListResponse;
  } catch (error) {
    if (process.env.NODE_ENV !== "production") {
      console.error("Error fetching matched jobs:", error);
    }
    return { items: [], total: 0, page: 1, page_size: 20 };
  }
}
