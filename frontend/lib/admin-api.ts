import { z } from 'zod';
import {
  BackendError,
  createAuthHeaders,
  parseBackendError,
  requireBackendToken,
} from './api.server';
import { BACKEND_URL } from './config';

export type AdminResult<T> = { data: T; error?: undefined } | { data?: undefined; error: string };

export async function fetchAdminEndpoint<T>(
  path: string,
  init: RequestInit = {},
  schema?: z.ZodSchema<T>,
  fallbackError = 'Request failed'
): Promise<AdminResult<T>> {
  try {
    const token = await requireBackendToken();
    const extraHeaders = (init.headers as Record<string, string> | undefined) ?? {};
    const response = await fetch(`${BACKEND_URL}${path}`, {
      ...init,
      headers: createAuthHeaders(token, extraHeaders),
      cache: 'no-store',
    });

    if (!response.ok) {
      return { error: (await parseBackendError(response)) || fallbackError };
    }

    const raw = await response.json();

    if (schema) {
      const parsed = schema.safeParse(raw);
      if (!parsed.success) {
        if (process.env.NODE_ENV !== 'production') {
          console.error('Admin response schema validation failed:', parsed.error);
        }
        return { error: fallbackError };
      }
      return { data: parsed.data };
    }

    return { data: raw as T };
  } catch (error) {
    if (error instanceof BackendError) {
      return { error: error.message };
    }
    return { error: fallbackError };
  }
}

export async function fetchAdminText(
  path: string,
  fallbackError = 'Request failed'
): Promise<AdminResult<string>> {
  try {
    const token = await requireBackendToken();
    const response = await fetch(`${BACKEND_URL}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });

    if (!response.ok) {
      return { error: (await parseBackendError(response)) || fallbackError };
    }

    return { data: await response.text() };
  } catch (error) {
    if (error instanceof BackendError) {
      return { error: error.message };
    }
    return { error: fallbackError };
  }
}

export async function fetchAdminData<T>(path: string, schema?: z.ZodSchema<T>): Promise<T | null> {
  try {
    const token = await requireBackendToken();
    const response = await fetch(`${BACKEND_URL}${path}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      return null;
    }

    const raw = await response.json();

    if (schema) {
      const parsed = schema.safeParse(raw);
      if (!parsed.success) {
        if (process.env.NODE_ENV !== 'production') {
          console.error('Admin data schema validation failed:', parsed.error);
        }
        return null;
      }
      return parsed.data;
    }

    return raw as T;
  } catch {
    return null;
  }
}

export { backendFetch } from './api.server';
