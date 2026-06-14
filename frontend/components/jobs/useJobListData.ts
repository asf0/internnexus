'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { fetchMatchPage } from '@/app/actions/match';
import { fetchJobs } from '@/lib/api';
import { DEFAULT_PAGE_SIZE } from '@/lib/constants';
import type { Job } from '@/lib/types/job';

interface UseJobListDataProps {
  readonly serverJobs: Job[] | undefined;
  readonly serverTotal: number | undefined;
  readonly serverTotalPages: number | undefined;
  readonly currentPage: number;
  readonly matched: boolean;
  readonly savedJobIds: Set<string>;
  readonly sessionId: string | null;
  readonly isMatchStateLoading: boolean;
  readonly clearMatches: () => void;
}

export function useJobListData({
  serverJobs,
  serverTotal,
  serverTotalPages,
  currentPage,
  matched,
  savedJobIds,
  sessionId,
  isMatchStateLoading,
  clearMatches,
}: UseJobListDataProps) {
  const searchParams = useSearchParams();

  const [clientJobs, setClientJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(matched);
  const [clientTotal, setClientTotal] = useState(0);
  const [appendedJobs, setAppendedJobs] = useState<Job[]>([]);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [lastLoadedPage, setLastLoadedPage] = useState(currentPage);

  const searchQuery = searchParams.get('search') || '';
  const company = searchParams.get('company') || '';
  const location = searchParams.get('location') || '';
  const category = searchParams.get('category') || '';
  const jobType = searchParams.get('job_type') || '';
  const workMode = searchParams.get('work_mode') || '';
  const postedWithin = searchParams.get('posted_within') || '';
  const savedOnly = searchParams.get('saved_only') === '1';

  const jobs = matched ? clientJobs : [...(serverJobs || []), ...appendedJobs];
  const total = matched ? clientTotal : serverTotal || 0;
  const totalPagesComputed = matched
    ? Math.ceil(clientTotal / DEFAULT_PAGE_SIZE)
    : serverTotalPages || 1;

  useEffect(() => {
    if (!matched) return;
    if (isMatchStateLoading) return;

    const loadMatchedJobs = async () => {
      setIsLoading(true);
      try {
        if (!sessionId) {
          setClientJobs([]);
          setClientTotal(0);
          return;
        }

        const data = await fetchMatchPage(sessionId, currentPage, DEFAULT_PAGE_SIZE, {
          search: searchQuery,
          company,
          location,
          category,
          job_type: jobType,
          work_mode: workMode,
          posted_within: postedWithin,
        });

        if (data.error) {
          if (data.error.includes('session expired')) {
            clearMatches();
          }
          setClientJobs([]);
          setClientTotal(0);
        } else {
          const jobsFromMatches: Job[] = data.matches.map((match) => ({
            id: match.job_id,
            source: '',
            title: match.title,
            company: match.company,
            location: match.location,
            city: match.city ?? null,
            state: match.state ?? null,
            country: match.country ?? null,
            apply_url: match.apply_url,
            description_text: match.description_text,
            job_category: match.job_category ?? null,
            job_type: match.job_type ?? null,
            work_mode: match.work_mode ?? null,
            posted_at: match.posted_at ?? null,
            is_active: true,
          }));
          const filteredJobs = savedOnly
            ? jobsFromMatches.filter((job) => savedJobIds.has(job.id))
            : jobsFromMatches;
          setClientJobs(filteredJobs);
          setClientTotal(savedOnly ? filteredJobs.length : data.total);
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadMatchedJobs();
  }, [
    matched,
    isMatchStateLoading,
    sessionId,
    currentPage,
    searchQuery,
    company,
    location,
    category,
    jobType,
    workMode,
    postedWithin,
    savedOnly,
    savedJobIds,
    clearMatches,
  ]);

  useEffect(() => {
    if (matched) return;
    setAppendedJobs([]);
    setLastLoadedPage(currentPage);
  }, [
    matched,
    currentPage,
    searchQuery,
    company,
    location,
    category,
    jobType,
    workMode,
    postedWithin,
    savedOnly,
    serverJobs,
  ]);

  const handleLoadMore = useCallback(async () => {
    if (matched || isLoadingMore) return;

    const nextPage = lastLoadedPage + 1;
    if (nextPage > totalPagesComputed) return;

    setIsLoadingMore(true);
    try {
      const data = await fetchJobs({
        page: nextPage,
        page_size: DEFAULT_PAGE_SIZE,
        search: searchQuery,
        company,
        location,
        category,
        job_type: jobType,
        work_mode: workMode,
        posted_within: postedWithin,
        saved_only: savedOnly ? '1' : undefined,
      });

      setAppendedJobs((prev) => {
        const existingIds = new Set([
          ...(serverJobs || []).map((job) => job.id),
          ...prev.map((job) => job.id),
        ]);
        const fresh = data.items.filter((job) => !existingIds.has(job.id));
        return [...prev, ...fresh];
      });
      setLastLoadedPage(nextPage);
    } finally {
      setIsLoadingMore(false);
    }
  }, [
    matched,
    isLoadingMore,
    lastLoadedPage,
    totalPagesComputed,
    searchQuery,
    company,
    location,
    category,
    jobType,
    workMode,
    postedWithin,
    savedOnly,
    serverJobs,
  ]);

  return {
    jobs,
    total,
    totalPagesComputed,
    isLoading,
    isLoadingMore,
    handleLoadMore,
  };
}
