'use server';

import { DayClickStatsSchema } from '@/lib/schemas';
import { fetchAdminEndpoint } from '@/lib/admin-api';
import type { ClicksByUser, DayClickStats } from './types';

export async function fetchClicksByUser(
  limit?: number
): Promise<{ data?: ClicksByUser[]; error?: string }> {
  const searchParams = new URLSearchParams();
  if (limit) searchParams.set('limit', String(limit));

  return fetchAdminEndpoint<ClicksByUser[]>(
    `/admin/clicks/by-user?${searchParams.toString()}`,
    { cache: 'no-store' },
    undefined,
    'Failed to fetch clicks by user'
  );
}

export async function fetchDayClickStats(
  date: string
): Promise<{ data?: DayClickStats; error?: string }> {
  return fetchAdminEndpoint<DayClickStats>(
    `/admin/clicks/date/${date}`,
    { cache: 'no-store' },
    DayClickStatsSchema,
    'Failed to fetch day click stats'
  );
}
