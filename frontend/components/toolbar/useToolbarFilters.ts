'use client';

import { useState, useEffect, useRef, useTransition, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useDebounce } from 'use-debounce';

export function useToolbarFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const [showFilters, setShowFilters] = useState(false);
  const currentSearch = searchParams.get('search') || '';
  const [searchInput, setSearchInput] = useState(currentSearch);
  const [debouncedSearch] = useDebounce(searchInput, 400);
  const isInitialMount = useRef(true);

  const companyStr = searchParams.get('company') || '';
  const locationStr = searchParams.get('location') || '';
  const categoryStr = searchParams.get('category') || '';
  const jobTypeStr = searchParams.get('job_type') || '';
  const workModeStr = searchParams.get('work_mode') || '';
  const currentPostedWithin = searchParams.get('posted_within') || '';
  const currentSavedOnly = searchParams.get('saved_only') === '1';
  const isMatched = searchParams.get('matched') === 'true';

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
      search: currentSearch,
    }),
    [
      currentCompanies,
      currentLocations,
      currentCategories,
      currentJobTypes,
      currentWorkModes,
      currentPostedWithin,
      currentSearch,
    ]
  );

  const [debouncedFilters] = useDebounce(filterValues, 300);

  useEffect(() => {
    if (debouncedSearch !== currentSearch) {
      updateFilter('search', debouncedSearch);
    }
  }, [debouncedSearch, currentSearch]);

  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      setSearchInput(currentSearch);
    }
  }, [currentSearch]);

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

  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.delete('page');
    startTransition(() => {
      router.push(`/?${params.toString()}`);
    });
  };

  const updateMultiSelect = (key: string, values: string[]) => {
    updateFilter(key, values.join('|'));
  };

  const clearFilters = () => {
    startTransition(() => {
      router.push('/');
    });
  };

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
