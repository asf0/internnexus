'use client';

import { useState, useEffect, useRef, useTransition } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { matchProfileResume, matchResume, fetchMatchFacets } from '@/app/actions/match';
import { useMatchState } from '@/lib/hooks/useMatchState';
import { LOCAL_STORAGE_KEYS, SESSION_STORAGE_KEYS } from '@/lib/constants';
import type { MatchResponse, MatchFacetsResponse } from '@/lib/types/job';

const MATCH_STATE_UPDATED_EVENT = 'internnexus:match-state-updated';

export function useToolbarMatch() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const { sessionId } = useMatchState();

  const [showResume, setShowResume] = useState(false);
  const [matchResult, setMatchResult] = useState<MatchResponse | null>(null);
  const [isMatching, setIsMatching] = useState(false);
  const [facets, setFacets] = useState<MatchFacetsResponse | null>(null);
  const [isLoadingFacets, setIsLoadingFacets] = useState(false);

  const isFetchingFacets = useRef(false);
  const lastFetchedFiltersRef = useRef<string | null>(null);

  const openResumeParam = searchParams.get('open_resume') === '1';

  useEffect(() => {
    if (openResumeParam) {
      setShowResume(true);
    }
  }, [openResumeParam]);

  const loadFacets = async (
    debouncedFilters: {
      search: string;
      companies: string[];
      locations: string[];
      categories: string[];
      jobTypes: string[];
      workModes: string[];
      postedWithin: string;
    },
    isMatched: boolean
  ) => {
    if (!isMatched || !sessionId) {
      setFacets(null);
      lastFetchedFiltersRef.current = null;
      return;
    }

    const filterKey = JSON.stringify({
      sessionId,
      search: debouncedFilters.search,
      company: debouncedFilters.companies.join('|'),
      location: debouncedFilters.locations.join('|'),
      category: debouncedFilters.categories.join('|'),
      job_type: debouncedFilters.jobTypes.join('|'),
      work_mode: debouncedFilters.workModes.join('|'),
      posted_within: debouncedFilters.postedWithin,
    });

    if (lastFetchedFiltersRef.current === filterKey) return;
    if (isFetchingFacets.current) return;

    isFetchingFacets.current = true;
    lastFetchedFiltersRef.current = filterKey;
    setIsLoadingFacets(true);
    try {
      const data = await fetchMatchFacets(sessionId, {
        search: debouncedFilters.search,
        company: debouncedFilters.companies.join('|'),
        location: debouncedFilters.locations.join('|'),
        category: debouncedFilters.categories.join('|'),
        job_type: debouncedFilters.jobTypes.join('|'),
        work_mode: debouncedFilters.workModes.join('|'),
        posted_within: debouncedFilters.postedWithin,
      });
      setFacets(data);
    } catch {
      lastFetchedFiltersRef.current = null;
    } finally {
      setIsLoadingFacets(false);
      isFetchingFacets.current = false;
    }
  };

  const applyMatchResponse = (response: MatchResponse) => {
    setMatchResult(response);
    const params = new URLSearchParams(searchParams.toString());

    const resetMatchStorage = () => {
      localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);
      sessionStorage.removeItem(SESSION_STORAGE_KEYS.MATCH_SESSION);
      window.dispatchEvent(new Event(MATCH_STATE_UPDATED_EVENT));
    };

    if (response.error) {
      params.delete('matched');
      resetMatchStorage();
      params.delete('page');
      startTransition(() => {
        router.push(`/?${params.toString()}`);
      });
      return;
    }

    const matches = response.matches ?? [];
    const matchIds = matches.map((match) => match.job_id).filter(Boolean);

    if (matchIds.length > 0 && !response.session_id) {
      setMatchResult({
        ...response,
        error: 'Matches were found but the session could not be created. Please try again.',
      });
      params.delete('matched');
      resetMatchStorage();
      params.delete('page');
      startTransition(() => {
        router.push(`/?${params.toString()}`);
      });
      return;
    }

    const scoresMap: Record<string, number> = {};
    matches.forEach((match) => {
      scoresMap[match.job_id] = match.match_percentage;
    });

    if (matchIds.length > 0) {
      localStorage.setItem(LOCAL_STORAGE_KEYS.MATCH_SCORES, JSON.stringify(scoresMap));
      sessionStorage.setItem(SESSION_STORAGE_KEYS.MATCH_SESSION, response.session_id);
      window.dispatchEvent(new Event(MATCH_STATE_UPDATED_EVENT));
      params.set('matched', 'true');
    } else {
      params.delete('matched');
      resetMatchStorage();
    }

    params.delete('page');
    params.delete('open_resume');
    startTransition(() => {
      router.push(`/?${params.toString()}`);
    });
  };

  const handleResumeSubmit = async (formData: FormData) => {
    setIsMatching(true);
    try {
      const response = await matchResume(formData);
      applyMatchResponse(response);
    } finally {
      setIsMatching(false);
    }
  };

  const handleProfileResumeMatch = async () => {
    setIsMatching(true);
    try {
      const response = await matchProfileResume();
      applyMatchResponse(response);
    } finally {
      setIsMatching(false);
    }
  };

  const handleResumeFormSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    await handleResumeSubmit(formData);
  };

  const clearMatches = () => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('matched');
    params.delete('page');
    localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);
    sessionStorage.removeItem(SESSION_STORAGE_KEYS.MATCH_SESSION);
    window.dispatchEvent(new Event(MATCH_STATE_UPDATED_EVENT));
    startTransition(() => {
      router.push(`/?${params.toString()}`);
    });
  };

  return {
    isPending,
    sessionId,
    showResume,
    setShowResume,
    matchResult,
    isMatching,
    facets,
    isLoadingFacets,
    loadFacets,
    handleProfileResumeMatch,
    handleResumeFormSubmit,
    clearMatches,
    applyMatchResponse,
  };
}
