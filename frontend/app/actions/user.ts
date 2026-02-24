"use server";

import { getBackendToken } from "@/lib/auth.server";
import { revalidatePath } from "next/cache";
import { BACKEND_URL } from "@/lib/config";
import { parseApiError } from "@/lib/utils";
import type {
  NotificationItem,
  SavedJobRecord,
  UpdateUserData,
  UserProfile,
  UserResume,
} from "@/lib/types/user";

export async function fetchUserProfile(): Promise<UserProfile | null> {
  const backendToken = await getBackendToken();

  if (!backendToken) {
    return null;
  }

  try {
    const response = await fetch(`${BACKEND_URL}/users/me`, {
      headers: {
        Authorization: `Bearer ${backendToken}`,
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
    if (process.env.NODE_ENV !== "production") {
      console.error("Error fetching user profile:", error);
    }
    return null;
  }
}

export interface ChangePasswordData {
  current_password: string;
  new_password: string;
}

export async function updateUserProfile(data: UpdateUserData): Promise<{ success: boolean; error?: string }> {
  const backendToken = await getBackendToken();

  if (!backendToken) {
    return { success: false, error: "Not authenticated" };
  }

  try {
    const response = await fetch(`${BACKEND_URL}/users/me`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${backendToken}`,
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
    if (process.env.NODE_ENV !== "production") {
      console.error("Error updating user profile:", error);
    }
    return { success: false, error: "An unexpected error occurred" };
  }
}

export async function changePassword(data: ChangePasswordData): Promise<{ success: boolean; error?: string }> {
  const backendToken = await getBackendToken();

  if (!backendToken) {
    return { success: false, error: "Not authenticated" };
  }

  try {
    const response = await fetch(`${BACKEND_URL}/users/me/password`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${backendToken}`,
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: parseApiError(errorData) };
    }

    return { success: true };
  } catch (error) {
    if (process.env.NODE_ENV !== "production") {
      console.error("Error changing password:", error);
    }
    return { success: false, error: "An unexpected error occurred" };
  }
}

export async function deleteAccount(): Promise<{ success: boolean; error?: string }> {
  const backendToken = await getBackendToken();

  if (!backendToken) {
    return { success: false, error: "Not authenticated" };
  }

  try {
    const response = await fetch(`${BACKEND_URL}/users/me`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${backendToken}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: parseApiError(errorData) };
    }

    return { success: true };
  } catch (error) {
    if (process.env.NODE_ENV !== "production") {
      console.error("Error deleting account:", error);
    }
    return { success: false, error: "An unexpected error occurred" };
  }
}

// Backward compatibility alias
export const getUserProfile = fetchUserProfile;

export async function fetchUserResume(): Promise<UserResume | null> {
  const backendToken = await getBackendToken();
  if (!backendToken) return null;
  try {
    const response = await fetch(`${BACKEND_URL}/users/me/resume`, {
      headers: { Authorization: `Bearer ${backendToken}` },
      cache: "no-store",
    });
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

export async function uploadUserResume(file: File): Promise<{ success: boolean; data?: UserResume; error?: string }> {
  const backendToken = await getBackendToken();
  if (!backendToken) return { success: false, error: "Not authenticated" };
  try {
    const body = new FormData();
    body.append("file", file, file.name);
    const response = await fetch(`${BACKEND_URL}/users/me/resume`, {
      method: "POST",
      headers: { Authorization: `Bearer ${backendToken}` },
      body,
    });
    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: parseApiError(errorData) };
    }
    const data = (await response.json()) as UserResume;
    revalidatePath("/profile");
    return { success: true, data };
  } catch {
    return { success: false, error: "Failed to upload resume" };
  }
}

export async function deleteUserResume(): Promise<{ success: boolean; error?: string }> {
  const backendToken = await getBackendToken();
  if (!backendToken) return { success: false, error: "Not authenticated" };
  try {
    const response = await fetch(`${BACKEND_URL}/users/me/resume`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${backendToken}` },
    });
    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: parseApiError(errorData) };
    }
    revalidatePath("/profile");
    return { success: true };
  } catch {
    return { success: false, error: "Failed to delete resume" };
  }
}

export async function fetchNotifications(): Promise<NotificationItem[]> {
  const backendToken = await getBackendToken();
  if (!backendToken) return [];
  try {
    const response = await fetch(`${BACKEND_URL}/users/me/notifications`, {
      headers: { Authorization: `Bearer ${backendToken}` },
      cache: "no-store",
    });
    if (!response.ok) return [];
    return await response.json();
  } catch {
    return [];
  }
}

export async function fetchUnreadNotificationCount(): Promise<number> {
  const backendToken = await getBackendToken();
  if (!backendToken) return 0;
  try {
    const response = await fetch(`${BACKEND_URL}/users/me/notifications/unread-count`, {
      headers: { Authorization: `Bearer ${backendToken}` },
      cache: "no-store",
    });
    if (!response.ok) return 0;
    const data = (await response.json()) as { unread_count: number };
    return data.unread_count || 0;
  } catch {
    return 0;
  }
}

export async function markNotificationRead(notificationId: string): Promise<{ success: boolean; error?: string }> {
  const backendToken = await getBackendToken();
  if (!backendToken) return { success: false, error: "Not authenticated" };
  try {
    const response = await fetch(`${BACKEND_URL}/users/me/notifications/${notificationId}/read`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${backendToken}` },
    });
    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: parseApiError(errorData) };
    }
    revalidatePath("/profile");
    return { success: true };
  } catch {
    return { success: false, error: "Failed to update notification" };
  }
}

export async function markAllNotificationsRead(): Promise<{ success: boolean; error?: string }> {
  const backendToken = await getBackendToken();
  if (!backendToken) return { success: false, error: "Not authenticated" };
  try {
    const response = await fetch(`${BACKEND_URL}/users/me/notifications/read-all`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${backendToken}` },
    });
    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: parseApiError(errorData) };
    }
    revalidatePath("/profile");
    return { success: true };
  } catch {
    return { success: false, error: "Failed to update notifications" };
  }
}

export async function fetchSavedJobIds(): Promise<string[]> {
  const backendToken = await getBackendToken();
  if (!backendToken) return [];
  try {
    const response = await fetch(`${BACKEND_URL}/users/me/saved-jobs/ids`, {
      headers: { Authorization: `Bearer ${backendToken}` },
      cache: "no-store",
    });
    if (!response.ok) return [];
    const ids = (await response.json()) as string[];
    return Array.isArray(ids) ? ids : [];
  } catch {
    return [];
  }
}

export async function fetchAppliedJobIds(): Promise<string[]> {
  const backendToken = await getBackendToken();
  if (!backendToken) return [];
  try {
    const response = await fetch(`${BACKEND_URL}/users/me/applied-jobs/ids`, {
      headers: { Authorization: `Bearer ${backendToken}` },
      cache: "no-store",
    });
    if (!response.ok) return [];
    const ids = (await response.json()) as string[];
    return Array.isArray(ids) ? ids : [];
  } catch {
    return [];
  }
}

export async function fetchSavedJobs(): Promise<SavedJobRecord[]> {
  const backendToken = await getBackendToken();
  if (!backendToken) return [];
  try {
    const response = await fetch(`${BACKEND_URL}/users/me/saved-jobs`, {
      headers: { Authorization: `Bearer ${backendToken}` },
      cache: "no-store",
    });
    if (!response.ok) return [];
    return (await response.json()) as SavedJobRecord[];
  } catch {
    return [];
  }
}

export async function saveJob(jobId: string): Promise<{ success: boolean; error?: string }> {
  const backendToken = await getBackendToken();
  if (!backendToken) return { success: false, error: "Not authenticated" };
  try {
    const response = await fetch(`${BACKEND_URL}/users/me/saved-jobs/${jobId}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${backendToken}` },
    });
    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: parseApiError(errorData) };
    }
    revalidatePath("/");
    revalidatePath("/profile");
    return { success: true };
  } catch {
    return { success: false, error: "Failed to save job" };
  }
}

export async function unsaveJob(jobId: string): Promise<{ success: boolean; error?: string }> {
  const backendToken = await getBackendToken();
  if (!backendToken) return { success: false, error: "Not authenticated" };
  try {
    const response = await fetch(`${BACKEND_URL}/users/me/saved-jobs/${jobId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${backendToken}` },
    });
    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: parseApiError(errorData) };
    }
    revalidatePath("/");
    revalidatePath("/profile");
    return { success: true };
  } catch {
    return { success: false, error: "Failed to unsave job" };
  }
}

export async function markApplied(jobId: string): Promise<{ success: boolean; error?: string }> {
  const backendToken = await getBackendToken();
  if (!backendToken) return { success: false, error: "Not authenticated" };
  try {
    const response = await fetch(`${BACKEND_URL}/users/me/applied-jobs/${jobId}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${backendToken}` },
    });
    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: parseApiError(errorData) };
    }
    revalidatePath("/");
    revalidatePath("/profile");
    return { success: true };
  } catch {
    return { success: false, error: "Failed to mark applied" };
  }
}

export async function unmarkApplied(jobId: string): Promise<{ success: boolean; error?: string }> {
  const backendToken = await getBackendToken();
  if (!backendToken) return { success: false, error: "Not authenticated" };
  try {
    const response = await fetch(`${BACKEND_URL}/users/me/applied-jobs/${jobId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${backendToken}` },
    });
    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: parseApiError(errorData) };
    }
    revalidatePath("/");
    revalidatePath("/profile");
    return { success: true };
  } catch {
    return { success: false, error: "Failed to unmark applied" };
  }
}
