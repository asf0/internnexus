'use client';

import { useCallback, useEffect, useState } from 'react';
import { fetchJobDetail, type JobDetailView } from './fetchJobDetail';

export function useJobDetail(jobId: string | null) {
  const [detail, setDetail] = useState<JobDetailView | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isUnavailable, setIsUnavailable] = useState(false);
  const [requestJobId, setRequestJobId] = useState<string | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    if (!jobId) {
      setRequestJobId(null);
      setDetail(null);
      setIsLoading(false);
      setError(null);
      setIsUnavailable(false);
      return;
    }

    const controller = new AbortController();
    let active = true;

    setRequestJobId(jobId);
    setDetail(null);
    setIsLoading(true);
    setError(null);
    setIsUnavailable(false);

    void fetchJobDetail(jobId, controller.signal)
      .then((job) => {
        if (!active) return;
        if (!job) {
          setError('This job is no longer available.');
          setIsUnavailable(true);
          return;
        }
        setDetail(job);
      })
      .catch((fetchError: unknown) => {
        if (!active || (fetchError instanceof Error && fetchError.name === 'AbortError')) return;
        setError('Unable to load this job. Please try again.');
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [jobId, requestVersion]);

  const retry = useCallback(() => {
    setRequestVersion((version) => version + 1);
  }, []);

  const isCurrentRequest = requestJobId === jobId;
  return {
    detail: isCurrentRequest ? detail : null,
    isLoading: Boolean(jobId) && (!isCurrentRequest || isLoading),
    error: isCurrentRequest ? error : null,
    isUnavailable: isCurrentRequest && isUnavailable,
    retry,
  };
}
