"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";
import MultiSelect from "./MultiSelect";
import { SingleSelect, Input, Button } from "./ui";
import { CATEGORY_LABEL_MAP } from "../lib/constants";
import { Search } from "lucide-react";

interface JobFiltersProps {
  companies: string[];
  locations: string[];
  categories?: string[];
}

export default function JobFilters({ companies, locations, categories = [] }: JobFiltersProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();


  const currentSearch = searchParams.get("search") || "";
  const currentCompanies = searchParams.get("company")?.split("|").filter(Boolean) || [];
  const currentLocations = searchParams.get("location")?.split("|").filter(Boolean) || [];
  const currentCategories = searchParams.get("category")?.split("|").filter(Boolean) || [];
  const currentVisa = searchParams.get("visa_sponsored");
  const currentF1 = searchParams.get("f1_friendly");
  const currentJobType = searchParams.get("job_type") || "";
  const currentWorkMode = searchParams.get("work_mode") || "";

  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    
    // Reset to page 1 when filters change
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

  const hasActiveFilters = 
    currentSearch || 
    currentCompanies.length > 0 || 
    currentLocations.length > 0 || 
    currentCategories.length > 0 ||
    currentVisa || 
    currentF1 || 
    currentJobType || 
    currentWorkMode;

  const jobTypes = [
    { value: "internship", label: "Internship" },
    { value: "full-time", label: "Full-time" },
    { value: "part-time", label: "Part-time" },
  ];
  
  const workModes = [
    { value: "remote", label: "Remote" },
    { value: "hybrid", label: "Hybrid" },
    { value: "on-site", label: "On-site" },
  ];

  return (
    <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 dark:border-md-outline-variant dark:bg-md-surface-container-low">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-md-on-surface">Filter Jobs</h3>
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearFilters}
          >
            Clear all
          </Button>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Search */}
        <div className="lg:col-span-3">
          <Input
            type="text"
            placeholder="Search jobs, companies, locations..."
            defaultValue={currentSearch}
            onChange={(e) => updateFilter("search", e.target.value)}
            icon={Search}
          />
        </div>

        {/* Company Multi-Select */}
        <MultiSelect
          options={companies}
          selected={currentCompanies}
          onChange={(values) => updateMultiSelect("company", values)}
          placeholder="All Companies"
        />

        {/* Location Multi-Select */}
        <MultiSelect
          options={locations}
          selected={currentLocations}
          onChange={(values) => updateMultiSelect("location", values)}
          placeholder="All Locations"
        />

        {/* Category Multi-Select */}
        <MultiSelect
          options={categories.length > 0 ? categories : [
            "software_engineering",
            "product_management",
            "data_science_ai",
            "quantitative_finance",
            "hardware_engineering"
          ]}
          selected={currentCategories}
          onChange={(values) => updateMultiSelect("category", values)}
          placeholder="All Categories"
          labelMap={CATEGORY_LABEL_MAP}
        />

        {/* Job Type */}
        <SingleSelect
          options={jobTypes}
          value={currentJobType}
          onChange={(value) => updateFilter("job_type", value)}
          placeholder="All Job Types"
        />

        {/* Work Mode */}
        <SingleSelect
          options={workModes}
          value={currentWorkMode}
          onChange={(value) => updateFilter("work_mode", value)}
          placeholder="All Work Modes"
        />

      </div>

      {isPending && (
        <div className="text-xs text-slate-500 dark:text-md-on-surface-variant">Updating results...</div>
      )}
    </div>
  );
}
