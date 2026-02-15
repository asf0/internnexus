"use server";

import { auth } from "@/auth";
import { BACKEND_URL } from "@/lib/config";

export async function matchResume(formData: FormData): Promise<unknown> {
  const session = await auth();
  
  if (!session?.backendToken) {
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
      "Authorization": `Bearer ${session.backendToken}`,
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
