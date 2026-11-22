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
  const result = await getBackendToken();
  if (!result.ok) {
    throw new BackendError(401, 'Not authenticated');
  }
  return result.token;
}

export async function parseBackendError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return parseApiError(body) || `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

export interface BackendFailure {
  status: number;
  message: string;
  body?: unknown;
  schemaFailure?: boolean;
}

export type BackendResult<T> =
  { data: T; failure?: undefined } | { data?: undefined; failure: BackendFailure };

export type BackendRequestAuth = 'required' | 'optional' | 'none';

export interface BackendRequestOptions {
  auth?: BackendRequestAuth;
  parse?: 'json' | 'text';
}

async function parseBackendFailure(response: Response): Promise<BackendFailure> {
  try {
    const body = await response.json();
    return {
      status: response.status,
      message: parseApiError(body) || `Request failed (${response.status})`,
      body,
    };
  } catch {
    return { status: response.status, message: `Request failed (${response.status})` };
  }
}

/**
 * Single backend request path for required, optional, and anonymous calls.
 * Auth and network errors propagate as exceptions (callers decide whether to
 * convert them); HTTP and schema failures are returned as values.
 */
export async function requestBackend<T>(
  path: string,
  init: RequestInit = {},
  schema?: z.ZodSchema<T>,
  { auth = 'required', parse = 'json' }: BackendRequestOptions = {}
): Promise<BackendResult<T>> {
  let token: string | undefined;
  if (auth === 'required') {
    token = await requireBackendToken();
  } else if (auth === 'optional') {
    const result = await getBackendToken();
    if (result.ok) {
      token = result.token;
    }
  }

  const extraHeaders = (init.headers as Record<string, string> | undefined) ?? {};
  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...init,
    headers: token ? createAuthHeaders(token, extraHeaders) : extraHeaders,
    cache: 'no-store',
  });

  if (!response.ok) {
    return { failure: await parseBackendFailure(response) };
  }

  if (response.status === 204) {
    return { data: undefined as T };
  }

  if (parse === 'text') {
    return { data: (await response.text()) as T };
  }

  const raw = await response.json();

  if (schema) {
    const parsed = schema.safeParse(raw);
    if (!parsed.success) {
      if (process.env.NODE_ENV !== 'production') {
        console.error('Response schema validation failed:', parsed.error);
      }
      return {
        failure: {
          status: response.status,
          message: 'Invalid response from server',
          schemaFailure: true,
        },
      };
    }
    return { data: parsed.data };
  }

  return { data: raw as T };
}

export async function backendFetch<T>(
  path: string,
  init: RequestInit = {},
  schema?: z.ZodSchema<T>
): Promise<T> {
  const result = await requestBackend(path, init, schema);
  if (result.failure) {
    throw new BackendError(result.failure.status, result.failure.message);
  }
  return result.data;
}
