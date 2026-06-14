import { z } from 'zod';
import { getBackendToken } from './auth.server';
import { BACKEND_URL } from './config';
import { createAuthHeaders } from './http';
import { parseApiError } from './utils';

export class BackendError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'BackendError';
  }
}

export { createAuthHeaders } from './http';

export async function requireBackendToken(): Promise<string> {
  const token = await getBackendToken();
  if (!token) {
    throw new BackendError(401, 'Not authenticated');
  }
  return token;
}

export async function parseBackendError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return parseApiError(body) || `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

export async function backendFetch<T>(
  path: string,
  init: RequestInit = {},
  schema?: z.ZodSchema<T>
): Promise<T> {
  const token = await requireBackendToken();
  const extraHeaders = (init.headers as Record<string, string> | undefined) ?? {};
  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...init,
    headers: createAuthHeaders(token, extraHeaders),
    cache: 'no-store',
  });

  if (!response.ok) {
    const message = await parseBackendError(response);
    throw new BackendError(response.status, message);
  }

  const raw = await response.json();

  if (schema) {
    const parsed = schema.safeParse(raw);
    if (!parsed.success) {
      if (process.env.NODE_ENV !== 'production') {
        console.error('Response schema validation failed:', parsed.error);
      }
      throw new BackendError(response.status, 'Invalid response from server');
    }
    return parsed.data;
  }

  return raw as T;
}
