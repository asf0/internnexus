'use client';

import { useState, useEffect } from 'react';
import { fetchClicksByUser } from '@/app/actions/admin';
import type { ClicksByUser } from './types';

export function useClicksByUser(limit = 20) {
  const [clicksByUser, setClicksByUser] = useState<ClicksByUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      const result = await fetchClicksByUser(limit);
      if (result.error) {
        setError(result.error);
      } else if (result.data) {
        setClicksByUser(result.data);
      }
      setLoading(false);
    }
    load();
  }, [limit]);

  return { clicksByUser, loading, error };
}
