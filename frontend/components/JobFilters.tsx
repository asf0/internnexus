"use client";

import { Search } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTransition, useState } from "react";
import MultiSelect from "./MultiSelect";

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

  const jobTypes = ["internship", "full-time", "part-time"];
  const workModes = ["remote", "hybrid", "on-site"];
  
  const categoryLabelMap: Record<string, string> = {
    "software_engineering": "Software Engineering",
    "product_management": "Product Management",
    "data_science_ai": "Data Science & AI",
    "quantitative_finance": "Quantitative Finance",
    "hardware_engineering": "Hardware Engineering",
  };

  return (
    <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 dark:border-md-outline-variant dark:bg-md-surface-container-low">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-md-on-surface">Filter Jobs</h3>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-xs text-slate-500 hover:text-slate-700 dark:text-md-on-surface-variant dark:hover:text-slate-200"
          >
            Clear all
          </button>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Search */}
        <div className="relative lg:col-span-3">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search jobs, companies, locations..."
            defaultValue={currentSearch}
            onChange={(e) => updateFilter("search", e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-10 pr-4 text-sm text-slate-900 placeholder-slate-400 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface dark:placeholder-md-on-surface-variant dark:focus:border-slate-400 dark:focus:ring-slate-400"
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
          labelMap={categoryLabelMap}
        />


        <select
          value={currentJobType}
          onChange={(e) => updateFilter("job_type", e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface dark:focus:border-slate-400 dark:focus:ring-slate-400"
        >
          <option value="">All Job Types</option>
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
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface dark:focus:border-slate-400 dark:focus:ring-slate-400"
        >
          <option value="">All Work Modes</option>
          {workModes.map((mode) => (
            <option key={mode} value={mode}>
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </option>
          ))}
        </select>

        {/* Visa/F1 Checkboxes */}
        <div className="flex gap-2">
          <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container dark:hover:bg-md-surface-container-high">
            <input
              type="checkbox"
              checked={currentVisa === "true"}
              onChange={(e) => updateFilter("visa_sponsored", e.target.checked ? "true" : "")}
              className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-500 dark:border-md-outline-variant dark:bg-md-surface-container-high dark:text-md-on-surface"
            />
            <span className="text-slate-700 dark:text-md-on-surface-variant">Visa</span>
          </label>
          <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container dark:hover:bg-md-surface-container-high">
            <input
              type="checkbox"
              checked={currentF1 === "true"}
              onChange={(e) => updateFilter("f1_friendly", e.target.checked ? "true" : "")}
              className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-500 dark:border-md-outline-variant dark:bg-md-surface-container-high dark:text-md-on-surface"
            />
            <span className="text-slate-700 dark:text-md-on-surface-variant">F1</span>
          </label>
        </div>
      </div>

      {isPending && (
        <div className="text-xs text-slate-500 dark:text-md-on-surface-variant">Updating results...</div>
      )}
    </div>
  );
}
