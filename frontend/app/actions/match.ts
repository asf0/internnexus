"use server";

import type { Job, JobListResponse } from "../../lib/types";

export async function matchResume(formData: FormData): Promise<unknown> {
  const file = formData.get("resume") as File | null;
  if (!file) {
    return { error: "Resume file is required." };
  }

  const backendBaseUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  const body = new FormData();
  body.append("file", file, file.name);

  const response = await fetch(`${backendBaseUrl}/match`, {
    method: "POST",
    body
  });

  if (!response.ok) {
    return { error: "Failed to match resume." };
  }

  return response.json();
}

export async function fetchMatchedJobs(matchIds: string[], pageSize: number = 20): Promise<JobListResponse> {
  if (matchIds.length === 0) {
    return { items: [], total: 0, page: 1, page_size: pageSize };
  }

  const backendBaseUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  const response = await fetch(
    `${backendBaseUrl}/jobs?match_ids=${matchIds.join("|")}&page_size=${pageSize}`,
    { cache: "no-store" }
  );

  if (!response.ok) {
    return { items: [], total: 0, page: 1, page_size: pageSize };
  }

  return (await response.json()) as JobListResponse;
}
