"use server";

import { auth } from "@/auth";
import { revalidatePath } from "next/cache";

const backendBaseUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export interface UserProfile {
  id: string;
  email: string;
  name: string | null;
  image: string | null;
  created_at: string;
  bio: string | null;
  phone: string | null;
  location: string | null;
  job_title: string | null;
  company: string | null;
  industry: string | null;
  skills: string[];
  linkedin_url: string | null;
  portfolio_url: string | null;
  preferred_locations: string[];
  has_password: boolean;
}

export async function getUserProfile(): Promise<UserProfile | null> {
  const session = await auth();

  if (!session?.backendToken) {
    return null;
  }

  try {
    const response = await fetch(`${backendBaseUrl}/users/me`, {
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

export interface UpdateUserData {
  name?: string | null;
  bio?: string | null;
  phone?: string | null;
  location?: string | null;
  job_title?: string | null;
  company?: string | null;
  industry?: string | null;
  skills?: string[];
  linkedin_url?: string | null;
  portfolio_url?: string | null;
  preferred_locations?: string[];
}

export async function updateUserProfile(data: UpdateUserData): Promise<{ success: boolean; error?: string }> {
  const session = await auth();

  if (!session?.backendToken) {
    return { success: false, error: "Not authenticated" };
  }

  try {
    const response = await fetch(`${backendBaseUrl}/users/me`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.backendToken}`,
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: errorData.detail?.message || "Failed to update profile" };
    }

    revalidatePath("/profile");
    revalidatePath("/settings");
    return { success: true };
  } catch (error) {
    console.error("Error updating user profile:", error);
    return { success: false, error: "An unexpected error occurred" };
  }
}

export interface ChangePasswordData {
  current_password?: string;
  new_password: string;
}

export async function changePassword(data: ChangePasswordData): Promise<{ success: boolean; error?: string }> {
  const session = await auth();

  if (!session?.backendToken) {
    return { success: false, error: "Not authenticated" };
  }

  try {
    const response = await fetch(`${backendBaseUrl}/users/me/password`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.backendToken}`,
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: errorData.detail?.message || "Failed to change password" };
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
    const response = await fetch(`${backendBaseUrl}/users/me`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${session.backendToken}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: errorData.detail?.message || "Failed to delete account" };
    }

    return { success: true };
  } catch (error) {
    console.error("Error deleting account:", error);
    return { success: false, error: "An unexpected error occurred" };
  }
}
