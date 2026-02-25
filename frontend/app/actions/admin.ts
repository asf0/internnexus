"use server";

import { getBackendToken } from "@/lib/auth.server";
import { BACKEND_URL } from "@/lib/config";

// ============================================================================
// Types
// ============================================================================

export interface AdminJob {
  id: string;
  source: string;
  title: string;
  company: string;
  location: string;
  city: string | null;
  state: string | null;
  country: string | null;
  apply_url: string;
  description_text: string;
  job_category: string | null;
  job_type: string | null;
  work_mode: string | null;
  posted_at: string | null;
  is_active: boolean;
  click_count: number;
  created_at: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  name: string | null;
  is_active: boolean;
  created_at: string;
  has_password: boolean;
  admin_role: string | null;
  provider: string | null;
  notes: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages?: number;
}

export interface JobsListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  company?: string;
  category?: string;
  isActive?: boolean;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
}

export interface UsersListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  isAdmin?: boolean;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
}

export interface UserClick {
  id: string;
  job_id: string;
  job_title: string;
  company: string;
  apply_url: string;
  clicked_at: string;
  utm_source: string;
  utm_medium: string | null;
  utm_campaign: string | null;
}

export interface CreateJobRequest {
  title: string;
  company: string;
  location: string;
  apply_url: string;
  description_text: string;
  job_category?: string;
  job_type?: string;
  work_mode?: string;
  posted_at?: string;
}

export interface ClicksByUser {
  user_id: string | null;
  email: string | null;
  name: string | null;
  click_count: number;
}

export interface HourlyClicks {
  hour: number;
  clicks: number;
}

export interface TopJobByClicks {
  job_id: string;
  title: string;
  company: string;
  apply_url: string | null;
  click_count: number;
}

export interface DayClickStats {
  date: string;
  total_clicks: number;
  unique_jobs: number;
  unique_users: number;
  anonymous_clicks: number;
  clicks_by_hour: HourlyClicks[];
  top_jobs: TopJobByClicks[];
}

// ============================================================================
// Jobs API
// ============================================================================

export async function fetchJobs(params: JobsListParams = {}) {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const searchParams = new URLSearchParams();
    searchParams.set("page", String(params.page || 1));
    searchParams.set("page_size", String(params.pageSize || 20));

    if (params.search) searchParams.set("search", params.search);
    if (params.company) searchParams.set("company", params.company);
    if (params.category) searchParams.set("category", params.category);
    if (params.isActive !== undefined) searchParams.set("is_active", String(params.isActive));
    if (params.sortBy) {
      searchParams.set("sort_by", params.sortBy);
      searchParams.set("sort_order", params.sortOrder || "desc");
    }

    const response = await fetch(
      `${BACKEND_URL}/admin/jobs?${searchParams.toString()}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }
    );

    if (!response.ok) {
      return { error: "Failed to fetch jobs" };
    }

    const data: PaginatedResponse<AdminJob> = await response.json();
    return { data };
  } catch {
    return { error: "Failed to fetch jobs" };
  }
}

export async function fetchJob(jobId: string) {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(`${BACKEND_URL}/admin/jobs/${jobId}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });

    if (!response.ok) {
      return { error: "Failed to fetch job" };
    }

    return { data: await response.json() };
  } catch {
    return { error: "Failed to fetch job" };
  }
}

export async function updateJob(jobId: string, data: Record<string, unknown>) {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(`${BACKEND_URL}/admin/jobs/${jobId}`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      return { error: "Failed to update job" };
    }

    return { data: await response.json() };
  } catch {
    return { error: "Failed to update job" };
  }
}

export async function deactivateJob(jobId: string) {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(`${BACKEND_URL}/admin/jobs/${jobId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      return { error: "Failed to deactivate job" };
    }

    return { success: true };
  } catch {
    return { error: "Failed to deactivate job" };
  }
}

export async function createJob(
  jobData: CreateJobRequest
): Promise<{ data?: AdminJob; error?: string }> {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(`${BACKEND_URL}/admin/jobs`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(jobData),
    });

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to create job" };
    }

    const data: AdminJob = await response.json();
    return { data };
  } catch {
    return { error: "Failed to create job" };
  }
}

export async function hardDeleteJob(
  jobId: string
): Promise<{ success?: boolean; error?: string }> {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(`${BACKEND_URL}/admin/jobs/${jobId}/hard`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to delete job" };
    }

    return { success: true };
  } catch {
    return { error: "Failed to delete job" };
  }
}

export async function bulkJobAction(
  jobIds: string[],
  action: "activate" | "deactivate" | "delete"
): Promise<{ data?: { affected: number }; error?: string }> {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(`${BACKEND_URL}/admin/jobs/bulk`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ job_ids: jobIds, action }),
    });

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to perform bulk action" };
    }

    const data = await response.json();
    return { data };
  } catch {
    return { error: "Failed to perform bulk action" };
  }
}

// ============================================================================
// Users API
// ============================================================================

export async function fetchUsers(params: UsersListParams = {}) {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const searchParams = new URLSearchParams();
    searchParams.set("page", String(params.page || 1));
    searchParams.set("page_size", String(params.pageSize || 20));

    if (params.search) searchParams.set("search", params.search);
    if (params.isAdmin !== undefined) searchParams.set("is_admin", String(params.isAdmin));
    if (params.sortBy) {
      searchParams.set("sort_by", params.sortBy);
      searchParams.set("sort_order", params.sortOrder || "desc");
    }

    const response = await fetch(
      `${BACKEND_URL}/admin/users?${searchParams.toString()}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }
    );

    if (!response.ok) {
      return { error: "Failed to fetch users" };
    }

    const data: PaginatedResponse<AdminUser> = await response.json();
    return { data };
  } catch {
    return { error: "Failed to fetch users" };
  }
}

export async function fetchUser(userId: string) {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(`${BACKEND_URL}/admin/users/${userId}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });

    if (!response.ok) {
      return { error: "Failed to fetch user" };
    }

    return { data: await response.json() };
  } catch {
    return { error: "Failed to fetch user" };
  }
}

export async function grantAdmin(
  userId: string,
  role: "admin" | "super_admin",
  notes?: string
) {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(
      `${BACKEND_URL}/admin/users/${userId}/grant-admin`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ role, notes }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to grant admin access" };
    }

    return { data: await response.json() };
  } catch {
    return { error: "Failed to grant admin access" };
  }
}

export async function revokeAdmin(userId: string) {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(
      `${BACKEND_URL}/admin/users/${userId}/revoke-admin`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to revoke admin access" };
    }

    return { success: true };
  } catch {
    return { error: "Failed to revoke admin access" };
  }
}

export async function deactivateUser(userId: string) {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(
      `${BACKEND_URL}/admin/users/${userId}/deactivate`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to deactivate user" };
    }

    return { success: true };
  } catch {
    return { error: "Failed to deactivate user" };
  }
}

export async function reactivateUser(userId: string) {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(
      `${BACKEND_URL}/admin/users/${userId}/reactivate`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to reactivate user" };
    }

    return { success: true };
  } catch {
    return { error: "Failed to reactivate user" };
  }
}

export async function fetchCurrentAdmin() {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(`${BACKEND_URL}/admin/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });

    if (!response.ok) {
      return { error: "Failed to fetch admin info" };
    }

    return { data: await response.json() };
  } catch {
    return { error: "Failed to fetch admin info" };
  }
}

export async function createUser(
  email: string,
  password: string,
  name?: string
): Promise<{ data?: AdminUser; error?: string }> {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(`${BACKEND_URL}/admin/users`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password, name }),
    });

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to create user" };
    }

    const data: AdminUser = await response.json();
    return { data };
  } catch {
    return { error: "Failed to create user" };
  }
}

export async function deleteUser(
  userId: string
): Promise<{ success?: boolean; error?: string }> {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(
      `${BACKEND_URL}/admin/users/${userId}/hard`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to delete user" };
    }

    return { success: true };
  } catch {
    return { error: "Failed to delete user" };
  }
}

export async function resetUserPassword(
  userId: string
): Promise<{ success?: boolean; error?: string }> {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(
      `${BACKEND_URL}/admin/users/${userId}/reset-password`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to reset password" };
    }

    return { success: true };
  } catch {
    return { error: "Failed to reset password" };
  }
}

export async function getUserClicks(
  userId: string,
  page?: number,
  pageSize?: number
): Promise<{ data?: PaginatedResponse<UserClick>; error?: string }> {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const searchParams = new URLSearchParams();
    searchParams.set("page", String(page || 1));
    searchParams.set("page_size", String(pageSize || 20));

    const response = await fetch(
      `${BACKEND_URL}/admin/users/${userId}/clicks?${searchParams.toString()}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }
    );

    if (!response.ok) {
      return { error: "Failed to fetch user clicks" };
    }

    const data: PaginatedResponse<UserClick> = await response.json();
    return { data };
  } catch {
    return { error: "Failed to fetch user clicks" };
  }
}

export async function updateUserNotes(
  userId: string,
  notes: string | null
): Promise<{ success?: boolean; error?: string }> {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(
      `${BACKEND_URL}/admin/users/${userId}/notes`,
      {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ notes }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to update notes" };
    }

    return { success: true };
  } catch {
    return { error: "Failed to update notes" };
  }
}

export async function exportUsers(): Promise<{ data?: string; error?: string }> {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(`${BACKEND_URL}/admin/users/export`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });

    if (!response.ok) {
      return { error: "Failed to export users" };
    }

    const data = await response.text();
    return { data };
  } catch {
    return { error: "Failed to export users" };
  }
}

// ============================================================================
// Clicks API
// ============================================================================

export async function fetchClicksByUser(
  limit?: number
): Promise<{ data?: ClicksByUser[]; error?: string }> {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const searchParams = new URLSearchParams();
    if (limit) searchParams.set("limit", String(limit));

    const response = await fetch(
      `${BACKEND_URL}/admin/clicks/by-user?${searchParams.toString()}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }
    );

    if (!response.ok) {
      return { error: "Failed to fetch clicks by user" };
    }

    const data: ClicksByUser[] = await response.json();
    return { data };
  } catch {
    return { error: "Failed to fetch clicks by user" };
  }
}

export async function fetchDayClickStats(
  date: string
): Promise<{ data?: DayClickStats; error?: string }> {
  try {
    const token = await getBackendToken();
    if (!token) {
      return { error: "Not authenticated" };
    }

    const response = await fetch(`${BACKEND_URL}/admin/clicks/date/${date}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });

    if (!response.ok) {
      return { error: "Failed to fetch day click stats" };
    }

    return { data: await response.json() };
  } catch {
    return { error: "Failed to fetch day click stats" };
  }
}
