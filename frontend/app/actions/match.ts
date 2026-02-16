"use server";

import { getBackendToken } from "@/lib/auth.server";
import { BACKEND_URL } from "@/lib/config";
import type { MatchResponse } from "@/lib/types/job";

export async function matchResume(formData: FormData): Promise<MatchResponse> {

  const backendToken = await getBackendToken();
  
  if (!backendToken) {
    return { matches: [], total: 0, error: "Authentication required. Please sign in." };
  }

  const file = formData.get("resume") as File | null;
  if (!file) {
    return { matches: [], total: 0, error: "Resume file is required." };
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
      return { matches: [], total: 0, error: "Your session has expired. Please sign in again." };
    }
    return { matches: [], total: 0, error: "Failed to match resume." };
  }

  return response.json();
}
