"use client";

import { useState } from "react";
import { Search, SlidersHorizontal, Upload, ChevronDown, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";
import MultiSelect from "./MultiSelect";
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
  
  const [showFilters, setShowFilters] = useState(false);
  const [showResume, setShowResume] = useState(false);
  const [matchResult, setMatchResult] = useState<any>(null);
  const [isMatching, setIsMatching] = useState(false);

  const currentSearch = searchParams.get("search") || "";
  const currentCompanies = searchParams.get("company")?.split("|").filter(Boolean) || [];
  const currentLocations = searchParams.get("location")?.split("|").filter(Boolean) || [];
  const currentCategories = searchParams.get("category")?.split("|").filter(Boolean) || [];
  const currentJobType = searchParams.get("job_type") || "";
  const currentWorkMode = searchParams.get("work_mode") || "";
  const currentPostedWithin = searchParams.get("posted_within") || "";
  const isMatched = searchParams.get("matched") === "true";
  const matchCount = isMatched ? 1 : 0; // Simplified - we'll show "matched" indicator

  const activeFilterCount = [
    currentCompanies.length > 0,
    currentLocations.length > 0,
    currentCategories.length > 0,
    currentJobType,
    currentWorkMode,
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
        
        // Store match data in localStorage to avoid URL size limits
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

  return (
    <div className="sticky top-0 z-50 space-y-3 backdrop-blur-md bg-white/80 dark:bg-md-surface/80 py-2 -mx-4 px-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
      {/* Main Toolbar Row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search jobs, companies, locations..."
            defaultValue={currentSearch}
            onChange={(e) => updateFilter("search", e.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm text-slate-900 placeholder-slate-400 focus:border-md-primary focus:outline-none focus:ring-1 focus:ring-md-primary dark:border-md-outline-variant dark:bg-md-surface-container-low dark:text-md-on-surface dark:placeholder-slate-500 dark:focus:border-md-primary"
          />
        </div>

        {/* Filters Toggle Button */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
            showFilters || activeFilterCount > 0
              ? "border-md-primary bg-md-primary-container text-md-primary dark:border-md-primary dark:bg-md-primary-container dark:text-md-primary"
              : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container-low dark:text-md-on-surface-variant dark:hover:bg-md-surface-container"
          }`}
        >
          <SlidersHorizontal className="h-4 w-4" />
          <span>Filters</span>
          {activeFilterCount > 0 && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-md-primary text-xs text-white">
              {activeFilterCount}
            </span>
          )}
          <ChevronDown className={`h-4 w-4 transition-transform ${showFilters ? "rotate-180" : ""}`} />
        </button>

        {/* Resume Upload Toggle Button */}
        <button
          onClick={() => setShowResume(!showResume)}
          className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
            showResume
              ? "border-md-primary bg-md-primary-container text-md-primary dark:border-md-primary dark:bg-md-primary-container dark:text-md-primary"
              : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container-low dark:text-md-on-surface-variant dark:hover:bg-md-surface-container"
          }`}
        >
          <Upload className="h-4 w-4" />
          <span className="hidden sm:inline">Match Resume</span>
          {matchCount > 0 && (
            <span className="rounded-full bg-md-primary px-2 py-0.5 text-xs text-white">
              {matchCount}
            </span>
          )}
        </button>

        {/* Clear Filters */}
        {activeFilterCount > 0 && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 rounded-lg px-3 py-2.5 text-sm text-slate-500 hover:text-slate-700 dark:text-md-on-surface-variant dark:hover:text-md-on-surface"
          >
            <X className="h-4 w-4" />
            <span className="hidden sm:inline">Clear</span>
          </button>
        )}
      </div>

      {/* Expanded Filters Panel */}
      {showFilters && (
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface">
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
            <select
              value={currentJobType}
              onChange={(e) => updateFilter("job_type", e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface"
            >
              <option value="">Job Type</option>
              {jobTypes.map((type) => (
                <option key={type} value={type}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </option>
              ))}
            </select>

            {/* Work Mode */}
            <select
              value={currentWorkMode}
              onChange={(e) => updateFilter("work_mode", e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface"
            >
              <option value="">Work Mode</option>
              {workModes.map((mode) => (
                <option key={mode} value={mode}>
                  {mode.charAt(0).toUpperCase() + mode.slice(1)}
                </option>
              ))}
            </select>

            {/* Date Posted */}
            <select
              value={currentPostedWithin}
              onChange={(e) => updateFilter("posted_within", e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface"
            >
              <option value="">Date Posted</option>
              {postedWithinOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

       </div>
        </div>
      )}

      {/* Resume Upload Panel */}
      {showResume && (
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
            <button
              type="submit"
              disabled={isMatching}
              className="rounded-lg bg-md-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-md-primary-container disabled:opacity-50"
            >
              {isMatching ? "Matching..." : "Find Matches"}
            </button>
            {isMatched && (
              <button
                type="button"
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
                className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
              >
                Clear Matches
              </button>
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
