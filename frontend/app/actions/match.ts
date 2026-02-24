"use server";

import { getBackendToken } from "@/lib/auth.server";
import { BACKEND_URL } from "@/lib/config";
import type { MatchResponse } from "@/lib/types/job";

function emptyMatch(error: string): MatchResponse {
  return {
    matches: [],
    total: 0,
    session_id: "",
    page: 1,
    page_size: 20,
    total_pages: 0,
    error,
  };
}

export async function matchResume(formData: FormData): Promise<MatchResponse> {

  const backendToken = await getBackendToken();
  
  if (!backendToken) {
    return emptyMatch("Authentication required. Please sign in.");
  }

  const file = formData.get("resume") as File | null;
  if (!file) {
    return emptyMatch("Resume file is required.");
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
    let detail = "";
    try {
      const payload = await response.json();
      if (payload && typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (payload && Array.isArray(payload.detail)) {
        detail = payload.detail
          .map((item: { msg?: string }) => item?.msg)
          .filter(Boolean)
          .join("; ");
      }
    } catch {
      try {
        const raw = await response.text();
        if (raw) {
          detail = raw.slice(0, 240);
        }
      } catch {
        // Ignore parsing errors and use fallback message below.
      }
    }

    if (response.status === 401) {
      return emptyMatch("Your session has expired. Please sign in again.");
    }
    return {
      ...emptyMatch(""),
      error: detail || `Failed to match resume (HTTP ${response.status}).`,
    };
  }

  return response.json();
}

export async function matchProfileResume(): Promise<MatchResponse> {
  const backendToken = await getBackendToken();
  if (!backendToken) {
    return emptyMatch("Authentication required. Please sign in.");
  }

  const response = await fetch(`${BACKEND_URL}/match/profile`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${backendToken}`,
    },
  });

  if (!response.ok) {
    let detail = "";
    try {
      const payload = await response.json();
      if (payload && typeof payload.detail === "string") {
        detail = payload.detail;
      }
    } catch {
      // no-op
    }
    if (response.status === 401) {
      return emptyMatch("Your session has expired. Please sign in again.");
    }
    return emptyMatch(detail || `Failed to match profile resume (HTTP ${response.status}).`);
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
    return emptyMatch("Authentication required. Please sign in.");
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
      return emptyMatch("Your session has expired. Please sign in again.");
    }
    if (response.status === 404) {
      return emptyMatch("Match session expired. Please upload your resume again.");
    }
    return emptyMatch("Failed to load matches.");
  }

  return response.json();
}
