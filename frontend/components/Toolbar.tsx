"use client";

import { useState, useEffect, useRef, useTransition } from "react";
import { Search, SlidersHorizontal, Upload, ChevronDown, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useDebounce } from "use-debounce";
import MultiSelect from "./MultiSelect";
import { Button, Input, SingleSelect } from "./ui";
import { matchResume } from "../app/actions/match";
import { CATEGORY_LABEL_MAP, LOCAL_STORAGE_KEYS } from "../lib/constants";
import type { MatchResponse } from "@/lib/types/job";

interface ToolbarProps {
  companies: string[];
  locations: string[];
  categories?: string[];
  isAuthenticated?: boolean;
}

export default function Toolbar({ companies, locations, categories = [], isAuthenticated = false }: ToolbarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  
  const [showFilters, setShowFilters] = useState(false);
  const [showResume, setShowResume] = useState(false);
  const [matchResult, setMatchResult] = useState<MatchResponse | null>(null);
  const [isMatching, setIsMatching] = useState(false);
  
  // Local state for search input with debouncing
  const currentSearch = searchParams.get("search") || "";
  const [searchInput, setSearchInput] = useState(currentSearch);
  const [debouncedSearch] = useDebounce(searchInput, 400);
  const isInitialMount = useRef(true);
  
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

  const currentCompanies = searchParams.get("company")?.split("|").filter(Boolean) || [];
  const currentLocations = searchParams.get("location")?.split("|").filter(Boolean) || [];
  const currentCategories = searchParams.get("category")?.split("|").filter(Boolean) || [];
  const currentJobTypes = searchParams.get("job_type")?.split("|").filter(Boolean) || [];
  const currentWorkModes = searchParams.get("work_mode")?.split("|").filter(Boolean) || [];
  const currentPostedWithin = searchParams.get("posted_within") || "";
  const isMatched = searchParams.get("matched") === "true";
  const matchCount = isMatched ? 1 : 0;

  const activeFilterCount = [
    currentCompanies.length > 0,
    currentLocations.length > 0,
    currentCategories.length > 0,
    currentJobTypes.length > 0,
    currentWorkModes.length > 0,
    currentPostedWithin,
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
  const postedWithinOptions = [
    { value: "24h", label: "Past 24 hours" },
    { value: "week", label: "Past week" },
    { value: "month", label: "Past month" },
  ];

  const handleResumeSubmit = async (formData: FormData) => {
    setIsMatching(true);
    try {
      const response = await matchResume(formData);
      setMatchResult(response);
      if (response && "matches" in response && response.matches) {
        const matches = response.matches;
        const matchIds = matches.map((match) => match.job_id).filter(Boolean);
        
        const scoresMap: Record<string, number> = {};
        matches.forEach((match) => {
          scoresMap[match.job_id] = match.match_percentage;
        });
        localStorage.setItem(LOCAL_STORAGE_KEYS.MATCH_SCORES, JSON.stringify(scoresMap));
        localStorage.setItem(LOCAL_STORAGE_KEYS.MATCH_IDS, JSON.stringify(matchIds));
        
        const params = new URLSearchParams(searchParams.toString());
        if (matchIds.length > 0) {
          params.set("matched", "true");
        } else {
          params.delete("matched");
          localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);
          localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_IDS);
        }
        params.delete("page");
        startTransition(() => {
          router.push(`/?${params.toString()}`);
        });
      }
    } finally {
      setIsMatching(false);
    }
  };

  const isFiltersActive = showFilters || activeFilterCount > 0;
  const isResumeActive = showResume;

  return (
    <div className="sticky top-0 z-50 space-y-3 backdrop-blur-md bg-white/80 dark:bg-md-surface/80 py-2 -mx-4 px-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
      {/* Main Toolbar Row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[200px]">
          <Input
            type="text"
            placeholder='Search jobs... (try: "software engineer" AND remote)'
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e: React.KeyboardEvent) => {
              if (e.key === "Enter") {
                updateFilter("search", searchInput);
              }
            }}
            icon={Search}
          />
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
            <div className="absolute right-0 top-6 z-50 w-64 rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-600 opacity-0 shadow-lg transition-opacity group-hover:opacity-100 dark:border-md-outline dark:bg-md-surface-container dark:text-md-on-surface">
              <p className="mb-2 font-medium text-slate-700 dark:text-md-on-surface">Search syntax:</p>
              <ul className="space-y-1">
                <li><code className="rounded bg-slate-100 px-1 dark:bg-md-surface-container-high">&quot;exact phrase&quot;</code> - Exact match</li>
                <li><code className="rounded bg-slate-100 px-1 dark:bg-md-surface-container-high">python AND remote</code> - Both terms</li>
                <li><code className="rounded bg-slate-100 px-1 dark:bg-md-surface-container-high">python OR java</code> - Either term</li>
                <li><code className="rounded bg-slate-100 px-1 dark:bg-md-surface-container-high">python NOT senior</code> - Exclude</li>
                <li><code className="rounded bg-slate-100 px-1 dark:bg-md-surface-container-high">title:python</code> - Field search</li>
              </ul>
            </div>
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
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* Company */}
            <MultiSelect
              options={companies}
              selected={currentCompanies}
              onChange={(values) => updateMultiSelect("company", values)}
              placeholder="Company"
            />

            {/* Location */}
            <MultiSelect
              options={locations}
              selected={currentLocations}
              onChange={(values) => updateMultiSelect("location", values)}
              placeholder="Location"
            />

            {/* Category */}
            <MultiSelect
              options={categories.length > 0 ? categories : Object.keys(CATEGORY_LABEL_MAP)}
              selected={currentCategories}
              onChange={(values) => updateMultiSelect("category", values)}
              placeholder="Category"
              labelMap={CATEGORY_LABEL_MAP}
            />

            {/* Job Type */}
            <MultiSelect
              options={jobTypes}
              selected={currentJobTypes}
              onChange={(values) => updateMultiSelect("job_type", values)}
              placeholder="Job Type"
            />

            {/* Work Mode */}
            <MultiSelect
              options={workModes}
              selected={currentWorkModes}
              onChange={(values) => updateMultiSelect("work_mode", values)}
              placeholder="Work Mode"
            />

            {/* Date Posted */}
            <SingleSelect
              options={postedWithinOptions}
              value={currentPostedWithin}
              onChange={(value) => updateFilter("posted_within", value)}
              placeholder="Date Posted"
            />

       </div>
        </div>
      )}

      {/* Resume Upload Panel - Only show if logged in */}
      {isAuthenticated && showResume && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-md-outline-variant dark:bg-md-surface-container-low">
          <form
            action={handleResumeSubmit}
            className="flex flex-wrap items-end gap-4"
          >
            <div className="flex-1 min-w-[200px]">
              <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant">
                Upload your resume to find matching jobs
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
                  localStorage.removeItem(LOCAL_STORAGE_KEYS.MATCH_IDS);
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
              {matchCount > 0 ? "Matched" : "No matches found."}
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
