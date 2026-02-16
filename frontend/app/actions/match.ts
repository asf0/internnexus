"use server";

import { getBackendToken } from "@/lib/auth.server";
import { BACKEND_URL } from "@/lib/config";

export async function matchResume(formData: FormData): Promise<unknown> {
  console.log("[matchResume] Starting match...");
  
  const backendToken = await getBackendToken();
  
  console.log("[matchResume] Token result:", { hasToken: !!backendToken, tokenLength: backendToken?.length });
  
  if (!backendToken) {
    console.log("[matchResume] No backend token - returning auth error");
    return { error: "Authentication required. Please sign in." };
  }

  const file = formData.get("resume") as File | null;
  if (!file) {
    return { error: "Resume file is required." };
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
      return { error: "Your session has expired. Please sign in again." };
    }
    return { error: "Failed to match resume." };
  }

  return response.json();
}
