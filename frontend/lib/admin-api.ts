import { z } from 'zod';
import { BackendError, requestBackend } from './api.server';

export type AdminResult<T> = { data: T; error?: undefined } | { data?: undefined; error: string };

export async function fetchAdminEndpoint<T>(
  path: string,
  init: RequestInit = {},
  schema?: z.ZodSchema<T>,
  fallbackError = 'Request failed'
): Promise<AdminResult<T>> {
  try {
    const result = await requestBackend(path, init, schema);
    if (result.failure) {
      return {
        error: result.failure.schemaFailure
          ? fallbackError
          : result.failure.message || fallbackError,
      };
    }
    return { data: result.data };
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
    const result = await requestBackend<string>(path, {}, undefined, { parse: 'text' });
    if (result.failure) {
      return { error: result.failure.message || fallbackError };
    }
    return { data: result.data };
  } catch (error) {
    if (error instanceof BackendError) {
      return { error: error.message };
    }
    return { error: fallbackError };
  }
}

export async function fetchAdminData<T>(path: string, schema?: z.ZodSchema<T>): Promise<T | null> {
  try {
    const result = await requestBackend(
      path,
      { headers: { 'Content-Type': 'application/json' } },
      schema
    );
    if (result.failure) {
      return null;
    }
    return result.data;
  } catch {
    return null;
  }
}

export { backendFetch } from './api.server';
