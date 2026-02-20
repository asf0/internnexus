"use server";

import { getBackendToken } from "@/lib/auth.server";
import { BACKEND_URL } from "@/lib/config";
import type { MatchResponse } from "@/lib/types/job";

export async function matchResume(formData: FormData): Promise<MatchResponse> {

  const backendToken = await getBackendToken();
  
  if (!backendToken) {
    return { matches: [], total: 0, session_id: "", page: 1, page_size: 20, total_pages: 0, error: "Authentication required. Please sign in." };
  }

  const file = formData.get("resume") as File | null;
  if (!file) {
    return { matches: [], total: 0, session_id: "", page: 1, page_size: 20, total_pages: 0, error: "Resume file is required." };
  }

  const body = new FormData();
  body.append("file", file, file.name);

  const response = await fetch(`${BACKEND_URL}/match`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${backendToken}`,
    },
    body,
  });

  if (!response.ok) {
    if (response.status === 401) {
      return { matches: [], total: 0, session_id: "", page: 1, page_size: 20, total_pages: 0, error: "Your session has expired. Please sign in again." };
    }
    return { matches: [], total: 0, session_id: "", page: 1, page_size: 20, total_pages: 0, error: "Failed to match resume." };
  }

  return response.json();
}

export async function fetchMatchPage(
  sessionId: string,
  page: number = 1,
  pageSize: number = 20,
  filters?: {
    search?: string;
    company?: string;
    location?: string;
    category?: string;
    job_type?: string;
    work_mode?: string;
    posted_within?: string;
  }
): Promise<MatchResponse> {
  const backendToken = await getBackendToken();

  if (!backendToken) {
    return { matches: [], total: 0, session_id: "", page: 1, page_size: 20, total_pages: 0, error: "Authentication required. Please sign in." };
  }

  const params = new URLSearchParams();
  params.set("page", page.toString());
  params.set("page_size", pageSize.toString());
  if (filters?.search) params.set("search", filters.search);
  if (filters?.company) params.set("company", filters.company);
  if (filters?.location) params.set("location", filters.location);
  if (filters?.category) params.set("category", filters.category);
  if (filters?.job_type) params.set("job_type", filters.job_type);
  if (filters?.work_mode) params.set("work_mode", filters.work_mode);
  if (filters?.posted_within) params.set("posted_within", filters.posted_within);

  const response = await fetch(
    `${BACKEND_URL}/match/${sessionId}?${params.toString()}`,
    {
      headers: { "Authorization": `Bearer ${backendToken}` },
    }
  );

  if (!response.ok) {
    if (response.status === 401) {
      return { matches: [], total: 0, session_id: "", page: 1, page_size: 20, total_pages: 0, error: "Your session has expired. Please sign in again." };
    }
    if (response.status === 404) {
      return { matches: [], total: 0, session_id: "", page: 1, page_size: 20, total_pages: 0, error: "Match session expired. Please upload your resume again." };
    }
    return { matches: [], total: 0, session_id: "", page: 1, page_size: 20, total_pages: 0, error: "Failed to load matches." };
  }

  return response.json();
}
