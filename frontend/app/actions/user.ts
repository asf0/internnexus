"use server";

import { auth } from "@/auth";
import { revalidatePath } from "next/cache";
import { BACKEND_URL } from "@/lib/config";
import { parseApiError } from "@/lib/utils";
import type { UserProfile, UpdateUserData } from "@/lib/types/user";

export async function fetchUserProfile(): Promise<UserProfile | null> {
  const session = await auth();

  if (!session?.backendToken) {
    return null;
  }

  try {
    const response = await fetch(`${BACKEND_URL}/users/me`, {
      headers: {
        Authorization: `Bearer ${session.backendToken}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        return null;
      }
      throw new Error("Failed to fetch user profile");
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching user profile:", error);
    return null;
  }
}

export interface ChangePasswordData {
  current_password: string;
  new_password: string;
}

export async function updateUserProfile(data: UpdateUserData): Promise<{ success: boolean; error?: string }> {
  const session = await auth();

  if (!session?.backendToken) {
    return { success: false, error: "Not authenticated" };
  }

  try {
    const response = await fetch(`${BACKEND_URL}/users/me`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.backendToken}`,
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: parseApiError(errorData) };
    }

    revalidatePath("/profile");
    revalidatePath("/settings");
    return { success: true };
  } catch (error) {
    console.error("Error updating user profile:", error);
    return { success: false, error: "An unexpected error occurred" };
  }
}

export async function changePassword(data: ChangePasswordData): Promise<{ success: boolean; error?: string }> {
  const session = await auth();

  if (!session?.backendToken) {
    return { success: false, error: "Not authenticated" };
  }

  try {
    const response = await fetch(`${BACKEND_URL}/users/me/password`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.backendToken}`,
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: parseApiError(errorData) };
    }

    return { success: true };
  } catch (error) {
    console.error("Error changing password:", error);
    return { success: false, error: "An unexpected error occurred" };
  }
}

export async function deleteAccount(): Promise<{ success: boolean; error?: string }> {
  const session = await auth();

  if (!session?.backendToken) {
    return { success: false, error: "Not authenticated" };
  }

  try {
    const response = await fetch(`${BACKEND_URL}/users/me`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${session.backendToken}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: parseApiError(errorData) };
    }

    return { success: true };
  } catch (error) {
    console.error("Error deleting account:", error);
    return { success: false, error: "An unexpected error occurred" };
  }
}

// Backward compatibility alias
export const getUserProfile = fetchUserProfile;
