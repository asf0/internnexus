'use client';

import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useDebounce } from 'use-debounce';

const CONTROLLED_KEYS = [
  'search',
  'company',
  'location',
  'category',
  'job_type',
  'work_mode',
  'posted_within',
  'saved_only',
  'matched',
] as const;

type ToolbarFilterKey = (typeof CONTROLLED_KEYS)[number];

type ToolbarFilterDraft = Record<ToolbarFilterKey, string>;

type SearchParamReader = {
  get(name: string): string | null;
};

function draftFromSearchParams(searchParams: SearchParamReader): ToolbarFilterDraft {
  return {
    search: searchParams.get('search') || '',
    company: searchParams.get('company') || '',
    location: searchParams.get('location') || '',
    category: searchParams.get('category') || '',
    job_type: searchParams.get('job_type') || '',
    work_mode: searchParams.get('work_mode') || '',
    posted_within: searchParams.get('posted_within') || '',
    saved_only: searchParams.get('saved_only') || '',
    matched: searchParams.get('matched') || '',
  };
}

function isToolbarFilterKey(key: string): key is ToolbarFilterKey {
  return (CONTROLLED_KEYS as readonly string[]).includes(key);
}

function buildQueryStringFromDraft(draft: ToolbarFilterDraft, baseQuery: string): string {
  const params = new URLSearchParams(baseQuery);

  for (const key of CONTROLLED_KEYS) {
    params.delete(key);
  }

  for (const key of CONTROLLED_KEYS) {
    if (draft[key]) {
      params.set(key, draft[key]);
    }
  }

  params.delete('page');
  params.delete('selected');
  return params.toString();
}

export function useToolbarFilters() {
  const { push } = useRouter();
  const searchParams = useSearchParams();
  const searchParamsString = searchParams.toString();
  const [isPending, startTransition] = useTransition();

  const initialDraft = draftFromSearchParams(searchParams);
  const [draft, setDraft] = useState<ToolbarFilterDraft>(initialDraft);
  const draftRef = useRef(initialDraft);
  const [searchInput, setSearchInputState] = useState(initialDraft.search);
  const searchInputRef = useRef(initialDraft.search);
  const baseQueryRef = useRef(searchParamsString);
  const locallyPushedQueriesRef = useRef(new Set<string>());
  const suppressDebouncedSearchRef = useRef(false);

  const [showFilters, setShowFilters] = useState(false);
  const [debouncedSearch] = useDebounce(searchInput, 400);

  const setDraftState = useCallback((nextDraft: ToolbarFilterDraft) => {
    draftRef.current = nextDraft;
    setDraft(nextDraft);
  }, []);

  const setSearchInput = useCallback((value: string) => {
    searchInputRef.current = value;
    setSearchInputState(value);
  }, []);

  const rememberLocallyPushedQuery = useCallback((queryString: string) => {
    const pendingQueries = locallyPushedQueriesRef.current;
    pendingQueries.add(queryString);

    if (pendingQueries.size > 20) {
      const oldestQuery = pendingQueries.values().next().value;
      if (oldestQuery !== undefined) {
        pendingQueries.delete(oldestQuery);
      }
    }
  }, []);

  const pushDraft = useCallback(
    (nextDraft: ToolbarFilterDraft) => {
      const queryString = buildQueryStringFromDraft(nextDraft, baseQueryRef.current);
      baseQueryRef.current = queryString;
      rememberLocallyPushedQuery(queryString);

      startTransition(() => {
        push(queryString ? `/?${queryString}` : '/');
      });
    },
    [push, rememberLocallyPushedQuery]
  );

  const updateFilter = useCallback(
    (key: string, value: string) => {
      if (!isToolbarFilterKey(key)) {
        return;
      }

      const nextDraft: ToolbarFilterDraft = {
        ...draftRef.current,
        [key]: key === 'search' ? value.trim() : value,
      };

      if (key !== 'search') {
        nextDraft.search = searchInputRef.current.trim();
      }

      setDraftState(nextDraft);
      pushDraft(nextDraft);
    },
    [pushDraft, setDraftState]
  );

  const updateMultiSelect = useCallback(
    (key: string, values: string[]) => {
      updateFilter(key, values.join('|'));
    },
    [updateFilter]
  );

  useEffect(() => {
    baseQueryRef.current = searchParamsString;

    if (locallyPushedQueriesRef.current.delete(searchParamsString)) {
      return;
    }

    const nextDraft = draftFromSearchParams(new URLSearchParams(searchParamsString));
    suppressDebouncedSearchRef.current = true;
    setDraftState(nextDraft);
    setSearchInput(nextDraft.search);
  }, [searchParamsString, setDraftState, setSearchInput]);

  useEffect(() => {
    if (suppressDebouncedSearchRef.current) {
      suppressDebouncedSearchRef.current = false;
      return;
    }

    const normalizedSearch = debouncedSearch.trim();
    if (normalizedSearch !== draftRef.current.search) {
      updateFilter('search', normalizedSearch);
    }
  }, [debouncedSearch, updateFilter]);

  const companyStr = draft.company;
  const locationStr = draft.location;
  const categoryStr = draft.category;
  const jobTypeStr = draft.job_type;
  const workModeStr = draft.work_mode;
  const currentPostedWithin = draft.posted_within;
  const currentSavedOnly = draft.saved_only === '1';
  const isMatched = draft.matched === 'true';

  const currentCompanies = useMemo(() => companyStr.split('|').filter(Boolean), [companyStr]);
  const currentLocations = useMemo(() => locationStr.split('|').filter(Boolean), [locationStr]);
  const currentCategories = useMemo(() => categoryStr.split('|').filter(Boolean), [categoryStr]);
  const currentJobTypes = useMemo(() => jobTypeStr.split('|').filter(Boolean), [jobTypeStr]);
  const currentWorkModes = useMemo(() => workModeStr.split('|').filter(Boolean), [workModeStr]);

  const filterValues = useMemo(
    () => ({
      companies: currentCompanies,
      locations: currentLocations,
      categories: currentCategories,
      jobTypes: currentJobTypes,
      workModes: currentWorkModes,
      postedWithin: currentPostedWithin,
      search: draft.search,
    }),
    [
      currentCompanies,
      currentLocations,
      currentCategories,
      currentJobTypes,
      currentWorkModes,
      currentPostedWithin,
      draft.search,
    ]
  );

  const [debouncedFilters] = useDebounce(filterValues, 300);

  const activeFilterCount = [
    currentCompanies.length > 0,
    currentLocations.length > 0,
    currentCategories.length > 0,
    currentJobTypes.length > 0,
    currentWorkModes.length > 0,
    currentPostedWithin,
    currentSavedOnly,
    isMatched,
  ].filter(Boolean).length;

  const clearFilters = useCallback(() => {
    const emptyDraft = draftFromSearchParams(new URLSearchParams());
    setSearchInput('');
    setDraftState(emptyDraft);
    baseQueryRef.current = '';
    rememberLocallyPushedQuery('');

    startTransition(() => {
      push('/');
    });
  }, [push, rememberLocallyPushedQuery, setDraftState, setSearchInput]);

  return {
    isPending,
    showFilters,
    setShowFilters,
    searchInput,
    setSearchInput,
    currentCompanies,
    currentLocations,
    currentCategories,
    currentJobTypes,
    currentWorkModes,
    currentPostedWithin,
    currentSavedOnly,
    isMatched,
    debouncedFilters,
    activeFilterCount,
    updateFilter,
    updateMultiSelect,
    clearFilters,
  };
}
