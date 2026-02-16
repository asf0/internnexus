"use server";

import { BACKEND_URL } from "@/lib/config";
import { parseApiError } from "@/lib/utils";
import type { RegisterRequest } from "@/lib/types/auth";

export async function registerUser(data: RegisterRequest): Promise<{ 
  success: boolean; 
  error?: string; 
  errorType?: string;
}> {
  try {
    const response = await fetch(`${BACKEND_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    const responseData = await response.json();

    if (!response.ok) {
      const detail = responseData.detail || {};
      return { 
        success: false, 
        error: detail.message || "Registration failed. Please try again.",
        errorType: detail.error,
      };
    }

    return { success: true };
  } catch (error) {
    if (process.env.NODE_ENV !== "production") {
      console.error("Registration error:", error);
    }
    return { success: false, error: "An unexpected error occurred. Please try again." };
  }
}
