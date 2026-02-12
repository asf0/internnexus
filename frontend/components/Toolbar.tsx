"use client";

import { useState, useEffect } from "react";
import { Search, SlidersHorizontal, Upload, ChevronDown, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";
import { useSession } from "next-auth/react";
import { useDebounce } from "use-debounce";
import MultiSelect from "./MultiSelect";
import { Button, Input, SingleSelect } from "./ui";
import { matchResume } from "../app/actions/match";

interface ToolbarProps {
  companies: string[];
  locations: string[];
  categories?: string[];
}

const categoryLabelMap: Record<string, string> = {
  "software_engineering": "Software Engineering",
  "product_management": "Product Management",
  "data_science_ai": "Data Science & AI",
  "quantitative_finance": "Quantitative Finance",
  "hardware_engineering": "Hardware Engineering",
};

export default function Toolbar({ companies, locations, categories = [] }: ToolbarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const { data: session } = useSession();
  
  const [showFilters, setShowFilters] = useState(false);
  const [showResume, setShowResume] = useState(false);
  const [matchResult, setMatchResult] = useState<any>(null);
  const [isMatching, setIsMatching] = useState(false);
  
  // Local state for search input with debouncing
  const currentSearch = searchParams.get("search") || "";
  const [searchInput, setSearchInput] = useState(currentSearch);
  const [debouncedSearch] = useDebounce(searchInput, 400);
  
  // Update URL when debounced search value changes
  useEffect(() => {
    if (debouncedSearch !== currentSearch) {
      updateFilter("search", debouncedSearch);
    }
  }, [debouncedSearch, currentSearch]);

  // Sync search input with URL parameter when it changes externally
  useEffect(() => {
    setSearchInput(currentSearch);
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
      if (response && typeof response === "object" && "matches" in response) {
        const matches = (response as { matches?: Array<{ job_id: string; match_percentage: number }> }).matches || [];
        const matchIds = matches.map((match) => match.job_id).filter(Boolean);
        
        const scoresMap: Record<string, number> = {};
        matches.forEach((match) => {
          scoresMap[match.job_id] = match.match_percentage;
        });
        localStorage.setItem("matchScores", JSON.stringify(scoresMap));
        localStorage.setItem("matchIds", JSON.stringify(matchIds));
        
        const params = new URLSearchParams(searchParams.toString());
        if (matchIds.length > 0) {
          params.set("matched", "true");
        } else {
          params.delete("matched");
          localStorage.removeItem("matchScores");
          localStorage.removeItem("matchIds");
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
            placeholder="Search jobs, companies, locations..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e: React.KeyboardEvent) => {
              if (e.key === "Enter") {
                updateFilter("search", searchInput);
              }
            }}
            icon={Search}
          />
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
        {session?.user && (
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
              options={categories.length > 0 ? categories : Object.keys(categoryLabelMap)}
              selected={currentCategories}
              onChange={(values) => updateMultiSelect("category", values)}
              placeholder="Category"
              labelMap={categoryLabelMap}
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
      {session?.user && showResume && (
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
                  localStorage.removeItem("matchScores");
                  localStorage.removeItem("matchIds");
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
