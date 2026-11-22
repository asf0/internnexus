'use server';

import { BackendError, backendFetch, createAuthHeaders } from '@/lib/api.server';
import { getBackendToken } from '@/lib/auth.server';
import { BACKEND_URL } from '@/lib/config';
import { MatchFacetsResponseSchema, MatchResponseSchema } from '@/lib/schemas';
import type { MatchFacetsResponse, MatchResponse } from '@/lib/types/job';

const MATCH_REQUEST_TIMEOUT_MS = 90000;

type MatchFilters = {
  search?: string;
  company?: string;
  location?: string;
  category?: string;
  job_type?: string;
  work_mode?: string;
  posted_within?: string;
};

function emptyMatch(error: string): MatchResponse {
  return {
    matches: [],
    total: 0,
    session_id: '',
    page: 1,
    page_size: 20,
    total_pages: 0,
    error,
  };
}

async function fetchWithTimeout(input: string, init: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), MATCH_REQUEST_TIMEOUT_MS);
  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
}

async function parseMatchError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (payload && typeof payload.detail === 'string') {
      return payload.detail;
    }
    if (payload && Array.isArray(payload.detail)) {
      return payload.detail
        .map((item: { msg?: string }) => item?.msg)
        .filter(Boolean)
        .join('; ');
    }
  } catch {
    try {
      const raw = await response.text();
      if (raw) return raw.slice(0, 240);
    } catch {
      // Ignore parsing errors and use fallback message below.
    }
  }
  return '';
}

function buildMatchParams(
  filters?: MatchFilters,
  page?: number,
  pageSize?: number
): URLSearchParams {
  const params = new URLSearchParams();
  if (page !== undefined) params.set('page', page.toString());
  if (pageSize !== undefined) params.set('page_size', pageSize.toString());
  for (const [key, value] of Object.entries(filters ?? {})) {
    if (value) params.set(key, value);
  }
  return params;
}

export async function matchResume(formData: FormData): Promise<MatchResponse> {
  try {
    const file = formData.get('resume') as File | null;
    if (!file) {
      return emptyMatch('Resume file is required.');
    }

    const tokenResult = await getBackendToken();
    if (!tokenResult.ok) {
      return emptyMatch('Your session has expired. Please sign in again.');
    }
    const token = tokenResult.token;

    const body = new FormData();
    body.append('file', file, file.name);

    let response: Response;
    try {
      response = await fetchWithTimeout(`${BACKEND_URL}/match`, {
        method: 'POST',
        headers: createAuthHeaders(token),
        body,
      });
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return emptyMatch('Matching timed out. Please try again.');
      }
      return emptyMatch('Unable to reach matching service. Please try again.');
    }

    if (!response.ok) {
      if (response.status === 401) {
        return emptyMatch('Your session has expired. Please sign in again.');
      }
      const detail = await parseMatchError(response);
      return {
        ...emptyMatch(''),
        error: detail || `Failed to match resume (HTTP ${response.status}).`,
      };
    }

    return MatchResponseSchema.parse(await response.json());
  } catch {
    return emptyMatch('Matching service returned an invalid response.');
  }
}

export async function matchProfileResume(): Promise<MatchResponse> {
  const tokenResult = await getBackendToken();
  if (!tokenResult.ok) {
    return emptyMatch('Your session has expired. Please sign in again.');
  }
  const token = tokenResult.token;

  let response: Response;
  try {
    response = await fetchWithTimeout(`${BACKEND_URL}/match/profile`, {
      method: 'POST',
      headers: createAuthHeaders(token),
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      return emptyMatch('Matching timed out. Please try again.');
    }
    return emptyMatch('Unable to reach matching service. Please try again.');
  }

  if (!response.ok) {
    let detail = '';
    try {
      const payload = await response.json();
      if (payload && typeof payload.detail === 'string') {
        detail = payload.detail;
      }
    } catch {
      // no-op
    }
    if (response.status === 401) {
      return emptyMatch('Your session has expired. Please sign in again.');
    }
    return emptyMatch(detail || `Failed to match profile resume (HTTP ${response.status}).`);
  }

  try {
    return MatchResponseSchema.parse(await response.json());
  } catch {
    return emptyMatch('Matching service returned an invalid response.');
  }
}

export async function fetchMatchPage(
  sessionId: string,
  page: number = 1,
  pageSize: number = 20,
  filters?: MatchFilters
): Promise<MatchResponse> {
  const params = buildMatchParams(filters, page, pageSize);

  try {
    return await backendFetch(
      `/match/${sessionId}?${params.toString()}`,
      { cache: 'no-store' },
      MatchResponseSchema
    );
  } catch (error) {
    if (error instanceof BackendError) {
      if (error.status === 401) {
        return emptyMatch('Your session has expired. Please sign in again.');
      }
      if (error.status === 404) {
        return emptyMatch('Match session expired. Please upload your resume again.');
      }
      return emptyMatch(error.message);
    }
    return emptyMatch('Failed to load matches.');
  }
}

export async function fetchMatchFacets(
  sessionId: string,
  filters?: MatchFilters
): Promise<MatchFacetsResponse | null> {
  const params = buildMatchParams(filters);

  try {
    return await backendFetch(
      `/match/${sessionId}/facets?${params.toString()}`,
      { cache: 'no-store' },
      MatchFacetsResponseSchema
    );
  } catch {
    return null;
  }
}
