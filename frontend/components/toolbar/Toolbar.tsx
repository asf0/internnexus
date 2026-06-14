"use client";

import { useState, useEffect, useRef, useTransition, useMemo } from "react";
import { Search, SlidersHorizontal, Upload, ChevronDown, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useDebounce } from "use-debounce";
import { MultiSelect, LocationSelect } from "@/components/common";
import { Button, Input, SingleSelect } from "@/components/ui";
import { matchProfileResume, matchResume, fetchMatchFacets } from "@/app/actions/match";
import { useMatchState } from "@/lib/hooks/useMatchState";
import { LOCAL_STORAGE_KEYS, SESSION_STORAGE_KEYS } from "@/lib/constants";
import { formatCategoryLabel } from "@/lib/utils";
import type { MatchResponse, LocationItem, MatchFacetsResponse } from "@/lib/types/job";

const MATCH_STATE_UPDATED_EVENT = "internnexus:match-state-updated";

interface ToolbarProps {
  readonly companies: string[];
  readonly locations: LocationItem[];
  readonly categories?: string[];
  readonly isAuthenticated?: boolean;
}

export default function Toolbar({ companies, locations, categories = [], isAuthenticated = false }: ToolbarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const { sessionId } = useMatchState();

  const [showFilters, setShowFilters] = useState(false);
  const [showResume, setShowResume] = useState(false);
  const [matchResult, setMatchResult] = useState<MatchResponse | null>(null);
  const [isMatching, setIsMatching] = useState(false);
  const [facets, setFacets] = useState<MatchFacetsResponse | null>(null);
  const [isLoadingFacets, setIsLoadingFacets] = useState(false);

  // Local state for search input with debouncing
  const currentSearch = searchParams.get("search") || "";
  const [searchInput, setSearchInput] = useState(currentSearch);
  const [debouncedSearch] = useDebounce(searchInput, 400);
  const isInitialMount = useRef(true);
  const isFetchingFacets = useRef(false);
  const lastFetchedFiltersRef = useRef<string | null>(null);

  // Update URL when debounced search value changes
  useEffect(() => {
    if (debouncedSearch !== currentSearch) {
      updateFilter("search", debouncedSearch);
    }
  }, [debouncedSearch, currentSearch]);

  // Sync search input with URL parameter only on initial mount
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      setSearchInput(currentSearch);
    }
  }, [currentSearch]);

  // Use raw string params as primitive dependencies — avoids new array refs on every render
  const companyStr = searchParams.get("company") || "";
  const locationStr = searchParams.get("location") || "";
  const categoryStr = searchParams.get("category") || "";
  const jobTypeStr = searchParams.get("job_type") || "";
  const workModeStr = searchParams.get("work_mode") || "";
  const currentPostedWithin = searchParams.get("posted_within") || "";
  const currentSavedOnly = searchParams.get("saved_only") === "1";
  const isMatched = searchParams.get("matched") === "true";
  const openResumeParam = searchParams.get("open_resume") === "1";
  const matchCount = isMatched ? 1 : 0;

  // Derive split arrays from stable string primitives
  const currentCompanies = useMemo(() => companyStr.split("|").filter(Boolean), [companyStr]);
  const currentLocations = useMemo(() => locationStr.split("|").filter(Boolean), [locationStr]);
  const currentCategories = useMemo(() => categoryStr.split("|").filter(Boolean), [categoryStr]);
  const currentJobTypes = useMemo(() => jobTypeStr.split("|").filter(Boolean), [jobTypeStr]);
  const currentWorkModes = useMemo(() => workModeStr.split("|").filter(Boolean), [workModeStr]);

  // Memoize filter values — depends on primitives so only recomputes when URL actually changes
  const filterValues = useMemo(() => ({
    companies: companyStr.split("|").filter(Boolean),
    locations: locationStr.split("|").filter(Boolean),
    categories: categoryStr.split("|").filter(Boolean),
    jobTypes: jobTypeStr.split("|").filter(Boolean),
    workModes: workModeStr.split("|").filter(Boolean),
    postedWithin: currentPostedWithin,
    search: currentSearch,
  }), [companyStr, locationStr, categoryStr, jobTypeStr, workModeStr, currentPostedWithin, currentSearch]);

  // Debounce the memoized filter values
  const [debouncedFilters] = useDebounce(filterValues, 300);

  useEffect(() => {
    if (isAuthenticated && openResumeParam) {
      setShowResume(true);
    }
  }, [isAuthenticated, openResumeParam]);

  // Fetch dynamic facets when in matched mode
  useEffect(() => {
    if (!isMatched || !sessionId) {
      setFacets(null);
      lastFetchedFiltersRef.current = null;
      return;
    }

    // Serialize current filters for stable comparison (prevents re-fetch when references
    // change but values are identical)
    const filterKey = JSON.stringify({
      sessionId,
      search: debouncedFilters.search,
      company: debouncedFilters.companies.join("|"),
      location: debouncedFilters.locations.join("|"),
      category: debouncedFilters.categories.join("|"),
      job_type: debouncedFilters.jobTypes.join("|"),
      work_mode: debouncedFilters.workModes.join("|"),
      posted_within: debouncedFilters.postedWithin,
    });

    // Skip if we already fetched with these exact filters
    if (lastFetchedFiltersRef.current === filterKey) {
      return;
    }

    // Prevent concurrent requests
    if (isFetchingFacets.current) {
      return;
    }

    const loadFacets = async () => {
      isFetchingFacets.current = true;
      lastFetchedFiltersRef.current = filterKey;
      setIsLoadingFacets(true);
      try {
        const data = await fetchMatchFacets(
          sessionId,
          {
            search: debouncedFilters.search,
            company: debouncedFilters.companies.join("|"),
            location: debouncedFilters.locations.join("|"),
            category: debouncedFilters.categories.join("|"),
            job_type: debouncedFilters.jobTypes.join("|"),
            work_mode: debouncedFilters.workModes.join("|"),
            posted_within: debouncedFilters.postedWithin,
          }
        );
        setFacets(data);
      } catch {
        // Allow retry on error
        lastFetchedFiltersRef.current = null;
      } finally {
        setIsLoadingFacets(false);
        isFetchingFacets.current = false;
      }
    };

    loadFacets();
  }, [isMatched, sessionId, debouncedFilters]);

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
    params.delete("page");
    startTransition(() => {
      router.push(`/?${params.toString()}`);
    });
  };

  const updateMultiSelect = (key: string, values: string[]) => {
    updateFilter(key, values.join("|"));
  };

  const clearFilters = () => {
    startTransition(() => {
      router.push("/");
    });
  };

  const jobTypes = ["internship", "full-time", "part-time"];
  const workModes = ["remote", "hybrid", "on-site"];
  const jobTypeLabelMap: Record<string, string> = {
    internship: "Internship",
    "full-time": "Full-time",
    "part-time": "Part-time",
  };
  const workModeLabelMap: Record<string, string> = {
    remote: "Remote",
    hybrid: "Hybrid",
    "on-site": "On-site",
  };
  const postedWithinOptions = [
    { value: "24h", label: "Past 24 hours" },
    { value: "7d", label: "Past week" },
    { value: "30d", label: "Past month" },
  ];



  const applyMatchResponse = (response: MatchResponse) => {
    setMatchResult(response);
    const params = new URLSearchParams(searchParams.toString());

    if (response.error) {
      params.delete("matched");
      localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);
      sessionStorage.removeItem(SESSION_STORAGE_KEYS.MATCH_SESSION);
      window.dispatchEvent(new Event(MATCH_STATE_UPDATED_EVENT));
      params.delete("page");
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
        error: "Matches were found but the session could not be created. Please try again.",
      });
      params.delete("matched");
      localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);
      sessionStorage.removeItem(SESSION_STORAGE_KEYS.MATCH_SESSION);
      window.dispatchEvent(new Event(MATCH_STATE_UPDATED_EVENT));
      params.delete("page");
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
      params.set("matched", "true");
    } else {
      params.delete("matched");
      localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);
      sessionStorage.removeItem(SESSION_STORAGE_KEYS.MATCH_SESSION);
      window.dispatchEvent(new Event(MATCH_STATE_UPDATED_EVENT));
    }

    params.delete("page");
    params.delete("open_resume");
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

  const isFiltersActive = showFilters || activeFilterCount > 0;
  const isResumeActive = showResume;

  return (
    <div className="sticky top-0 z-50 space-y-3 backdrop-blur-md bg-white/80 dark:bg-md-surface/80 py-2 -mx-4 px-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
      {/* Main Toolbar Row */}
      <div className="relative flex flex-wrap items-center gap-3">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[200px]">
          <Input
            type="text"
            placeholder='Search jobs...'
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e: React.KeyboardEvent) => {
              if (e.key === "Enter") {
                updateFilter("search", searchInput);
              }
            }}
            icon={Search}
          />
          {searchInput && (
            <button
              type="button"
              onClick={() => {
                setSearchInput("");
                updateFilter("search", "");
              }}
              className="absolute right-8 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          <div className="absolute right-2 top-1/2 -translate-y-1/2 group">
            <button
              type="button"
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              title="Search tips"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
            {!showFilters && (
              <div className="pointer-events-none invisible absolute right-0 top-6 z-50 w-64 rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-600 opacity-0 shadow-lg transition-opacity group-hover:pointer-events-auto group-hover:visible group-hover:opacity-100 dark:border-md-outline dark:bg-md-surface-container dark:text-md-on-surface">
                <p className="mb-2 font-medium text-slate-700 dark:text-md-on-surface">Search syntax:</p>
                <ul className="space-y-1">
                  <li><code className="rounded bg-slate-100 px-1 dark:bg-md-surface-container-high">&quot;exact phrase&quot;</code> - Exact match</li>
                  <li><code className="rounded bg-slate-100 px-1 dark:bg-md-surface-container-high">python AND remote</code> - Both terms</li>
                  <li><code className="rounded bg-slate-100 px-1 dark:bg-md-surface-container-high">python OR java</code> - Either term</li>
                  <li><code className="rounded bg-slate-100 px-1 dark:bg-md-surface-container-high">python NOT senior</code> - Exclude</li>
                  <li><code className="rounded bg-slate-100 px-1 dark:bg-md-surface-container-high">title:python</code> - Field search</li>
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Filters Toggle Button */}
        <Button
          variant={isFiltersActive ? "primary" : "secondary"}
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2"
        >
          <SlidersHorizontal className="h-4 w-4" />
          <span>Filters</span>
          {activeFilterCount > 0 && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-md-primary text-xs text-white">
              {activeFilterCount}
            </span>
          )}
          <ChevronDown className={`h-4 w-4 transition-transform ${showFilters ? "rotate-180" : ""}`} />
        </Button>

        {/* Resume Upload Toggle Button - Only show if logged in */}
        {isAuthenticated && (
          <Button
            variant={isResumeActive ? "primary" : "secondary"}
            onClick={() => setShowResume(!showResume)}
            className="flex items-center gap-2"
          >
            <Upload className="h-4 w-4" />
            <span className="hidden sm:inline">Match Resume</span>
            {matchCount > 0 && (
              <span className="rounded-full bg-md-primary px-2 py-0.5 text-xs text-white">
                {matchCount}
              </span>
            )}
          </Button>
        )}

        {/* Clear Filters */}
        {activeFilterCount > 0 && (
          <Button variant="ghost" onClick={clearFilters} className="flex items-center gap-1">
            <X className="h-4 w-4" />
            <span className="hidden sm:inline">Clear</span>
          </Button>
        )}
      </div>

      {/* Expanded Filters Panel */}
      {showFilters && (
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface">
          {isLoadingFacets && (
            <div className="mb-2 text-xs text-slate-500 dark:text-md-on-surface-variant">
              Loading filter options...
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {/* Company */}
            <MultiSelect
              options={isMatched && facets 
                ? facets.companies.map(f => f.value).sort((a, b) => a.localeCompare(b))
                : [...companies].sort((a, b) => a.localeCompare(b))}
              selected={currentCompanies}
              onChange={(values) => updateMultiSelect("company", values)}
              placeholder="Company"
              disabled={isMatched && isLoadingFacets}
            />

            {/* Location */}
            <LocationSelect
              locations={isMatched && facets ? facets.locations : locations}
              selected={currentLocations}
              onChange={(values: string[]) => updateMultiSelect("location", values)}
              placeholder="Location"
              disabled={isMatched && isLoadingFacets}
            />

            {/* Category */}
            <MultiSelect
              options={isMatched && facets
                ? facets.categories.map(f => f.value).sort((a, b) => formatCategoryLabel(a).localeCompare(formatCategoryLabel(b)))
                : [...categories].sort((a, b) => formatCategoryLabel(a).localeCompare(formatCategoryLabel(b)))}
              selected={currentCategories}
              onChange={(values) => updateMultiSelect("category", values)}
              placeholder="Category"
              labelMap={isMatched && facets
                ? Object.fromEntries(facets.categories.map((c) => [c.value, formatCategoryLabel(c.value)]))
                : Object.fromEntries(categories.map((c) => [c, formatCategoryLabel(c)]))}
              disabled={isMatched && isLoadingFacets}
            />

            {/* Job Type */}
            <MultiSelect
              options={isMatched && facets
                ? facets.job_types.map(f => f.value)
                : jobTypes}
              selected={currentJobTypes}
              onChange={(values) => updateMultiSelect("job_type", values)}
              placeholder="Job Type"
              labelMap={jobTypeLabelMap}
              disabled={isMatched && isLoadingFacets}
            />

            {/* Work Mode */}
            <MultiSelect
              options={isMatched && facets
                ? facets.work_modes.map(f => f.value)
                : workModes}
              selected={currentWorkModes}
              onChange={(values) => updateMultiSelect("work_mode", values)}
              placeholder="Work Mode"
              labelMap={workModeLabelMap}
              disabled={isMatched && isLoadingFacets}
            />

            {/* Date Posted */}
            <SingleSelect
              options={postedWithinOptions}
              value={currentPostedWithin}
              onChange={(value) => updateFilter("posted_within", value)}
              placeholder="Date Posted"
            />

            <label className="flex min-h-[44px] items-center gap-2 rounded-lg border border-slate-300 px-3 text-sm text-slate-700 dark:border-md-outline dark:text-md-on-surface-variant">
              <input
                type="checkbox"
                checked={currentSavedOnly}
                disabled={!isAuthenticated}
                onChange={(event) => updateFilter("saved_only", event.target.checked ? "1" : "")}
                className="h-4 w-4"
              />
              <span>Saved Jobs</span>
              {!isAuthenticated && <span className="text-xs text-slate-500">(sign in)</span>}
            </label>

       </div>
        </div>
      )}

      {/* Resume Upload Panel - Only show if logged in */}
      {isAuthenticated && showResume && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-md-outline-variant dark:bg-md-surface-container-low">
          <div className="mb-4">
            <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant">
              Match using your saved profile resume
            </label>
            <Button
              type="button"
              disabled={isMatching}
              onClick={handleProfileResumeMatch}
            >
              {isMatching ? "Matching..." : "Find Matches (Saved Resume)"}
            </Button>
          </div>
          <div className="mb-3 text-xs text-slate-500 dark:text-md-on-surface-variant">
            Or upload a different file for a one-time match:
          </div>
          <form
            onSubmit={handleResumeFormSubmit}
            className="flex flex-wrap items-end gap-4"
          >
            <div className="flex-1 min-w-[200px]">
              <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant">
                Upload resume (one-time override)
              </label>
              <input
                name="resume"
                type="file"
                accept="application/pdf"
                className="w-full rounded-lg border border-slate-200 bg-white p-2 text-sm text-slate-900 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface dark:file:bg-slate-700 dark:file:text-slate-300"
              />
            </div>
            <Button
              type="submit"
              disabled={isMatching}
            >
              {isMatching ? "Matching..." : "Find Matches"}
            </Button>
            {isMatched && (
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  const params = new URLSearchParams(searchParams.toString());
                  params.delete("matched");
                  params.delete("page");
                  localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);
                  sessionStorage.removeItem(SESSION_STORAGE_KEYS.MATCH_SESSION);
                  window.dispatchEvent(new Event(MATCH_STATE_UPDATED_EVENT));
                  startTransition(() => {
                    router.push(`/?${params.toString()}`);
                  });
                }}
              >
                Clear Matches
              </Button>
            )}
          </form>
          {matchResult && !isMatching && (
            <div className="mt-3 text-sm text-slate-600 dark:text-md-on-surface-variant">
              {matchResult.error
                ? matchResult.error
                : matchResult.total > 0
                  ? matchResult.reused_from_cache
                    ? `Matched ${matchResult.total} job${matchResult.total === 1 ? "" : "s"} (reused your previous resume results).`
                    : `Matched ${matchResult.total} job${matchResult.total === 1 ? "" : "s"}.`
                  : "No matches found."}
            </div>
          )}
        </div>
      )}

      {isPending && (
        <div className="text-xs text-slate-500 dark:text-md-on-surface-variant">Updating...</div>
      )}
    </div>
  );
}
