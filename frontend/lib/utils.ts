import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Get color classes based on match percentage
 */
export function getMatchColor(percentage: number): string {
  if (percentage >= 80) return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
  if (percentage >= 60) return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300";
  if (percentage >= 40) return "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200";
  return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
}

/**
 * Safely parse JSON with fallback value
 */
export function safeJsonParse<T>(str: string | null, defaultValue: T): T {
  if (!str) return defaultValue;
  try {
    return JSON.parse(str);
  } catch {
    return defaultValue;
  }
}

/**
 * Parse API error response into user-friendly message
 */
export function parseApiError(error: unknown): string {
  if (error && typeof error === 'object') {
    // Check for { detail: { message: string } } structure
    if ('detail' in error) {
      const detail = (error as { detail?: { message?: string } | string }).detail;
      if (typeof detail === 'string') return detail;
      if (detail && typeof detail === 'object' && 'message' in detail) {
        return detail.message || "An error occurred";
      }
    }
    // Check for { message: string } structure
    if ('message' in error) {
      const message = (error as { message?: string }).message;
      if (typeof message === 'string') return message;
    }
  }
  return "An error occurred";
}

/**
 * Build full backend URL from path
 */
export function buildBackendUrl(path: string): string {
  const baseUrl = process.env.BACKEND_URL || 
                  process.env.NEXT_PUBLIC_BACKEND_URL || 
                  "http://localhost:8000";
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}${cleanPath}`;
}
