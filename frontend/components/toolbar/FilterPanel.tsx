'use client';

import { useEffect, useState } from 'react';
import { MultiSelect, LocationSelect } from '@/components/common';
import { SingleSelect } from '@/components/ui';
import { formatCategoryLabel } from '@/lib/utils';
import { fetchCompanyFilterOptions } from '@/app/actions/jobs';
import type { MatchFacetsResponse, LocationItem } from '@/lib/types/job';

interface FilterPanelProps {
  readonly isOpen: boolean;
  readonly isLoadingFacets: boolean;
  readonly isMatched: boolean;
  readonly facets: MatchFacetsResponse | null;
  readonly locations: LocationItem[];
  readonly categories: string[];
  readonly currentCompanies: string[];
  readonly currentLocations: string[];
  readonly currentCategories: string[];
  readonly currentJobTypes: string[];
  readonly currentWorkModes: string[];
  readonly currentPostedWithin: string;
  readonly currentSavedOnly: boolean;
  readonly isAuthenticated: boolean;
  readonly onMultiSelectChange: (key: string, values: string[]) => void;
  readonly onFilterChange: (key: string, value: string) => void;
}

const jobTypes = ['internship', 'full-time', 'part-time'];
const workModes = ['remote', 'hybrid', 'on-site'];

const jobTypeLabelMap: Record<string, string> = {
  internship: 'Internship',
  'full-time': 'Full-time',
  'part-time': 'Part-time',
};

const workModeLabelMap: Record<string, string> = {
  remote: 'Remote',
  hybrid: 'Hybrid',
  'on-site': 'On-site',
};

const postedWithinOptions = [
  { value: '24h', label: 'Past 24 hours' },
  { value: '7d', label: 'Past week' },
  { value: '30d', label: 'Past month' },
];

export function FilterPanel({
  isOpen,
  isLoadingFacets,
  isMatched,
  facets,
  locations,
  categories,
  currentCompanies,
  currentLocations,
  currentCategories,
  currentJobTypes,
  currentWorkModes,
  currentPostedWithin,
  currentSavedOnly,
  isAuthenticated,
  onMultiSelectChange,
  onFilterChange,
}: FilterPanelProps) {
  const [companyOptions, setCompanyOptions] = useState<string[]>([]);
  const [isLoadingCompanies, setIsLoadingCompanies] = useState(false);

  useEffect(() => {
    if (!isOpen || isMatched || companyOptions.length > 0) return;
    let cancelled = false;
    setIsLoadingCompanies(true);
    fetchCompanyFilterOptions()
      .then((options) => {
        if (!cancelled) setCompanyOptions(options);
      })
      .catch(() => {
        // Leave the list empty; the select renders its own empty state.
      })
      .finally(() => {
        if (!cancelled) setIsLoadingCompanies(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen, isMatched, companyOptions.length]);

  if (!isOpen) return null;

  return (
    <div className="border-border bg-surface text-foreground rounded-lg border px-3 py-2 text-sm">
      {isLoadingFacets && (
        <div className="text-foreground-muted mb-2 text-xs">Loading filter options...</div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <MultiSelect
          options={
            isMatched && facets
              ? facets.companies.map((f) => f.value).sort((a, b) => a.localeCompare(b))
              : [...companyOptions].sort((a, b) => a.localeCompare(b))
          }
          selected={currentCompanies}
          onChange={(values) => onMultiSelectChange('company', values)}
          placeholder="Company"
          disabled={isMatched && isLoadingFacets}
          loading={isLoadingCompanies}
        />

        <LocationSelect
          locations={isMatched && facets ? facets.locations : locations}
          selected={currentLocations}
          onChange={(values: string[]) => onMultiSelectChange('location', values)}
          placeholder="Location"
          disabled={isMatched && isLoadingFacets}
        />

        <MultiSelect
          options={
            isMatched && facets
              ? facets.categories
                  .map((f) => f.value)
                  .sort((a, b) => formatCategoryLabel(a).localeCompare(formatCategoryLabel(b)))
              : [...categories].sort((a, b) =>
                  formatCategoryLabel(a).localeCompare(formatCategoryLabel(b))
                )
          }
          selected={currentCategories}
          onChange={(values) => onMultiSelectChange('category', values)}
          placeholder="Category"
          labelMap={
            isMatched && facets
              ? Object.fromEntries(
                  facets.categories.map((c) => [c.value, formatCategoryLabel(c.value)])
                )
              : Object.fromEntries(categories.map((c) => [c, formatCategoryLabel(c)]))
          }
          disabled={isMatched && isLoadingFacets}
        />

        <MultiSelect
          options={isMatched && facets ? facets.job_types.map((f) => f.value) : jobTypes}
          selected={currentJobTypes}
          onChange={(values) => onMultiSelectChange('job_type', values)}
          placeholder="Job Type"
          labelMap={jobTypeLabelMap}
          disabled={isMatched && isLoadingFacets}
        />

        <MultiSelect
          options={isMatched && facets ? facets.work_modes.map((f) => f.value) : workModes}
          selected={currentWorkModes}
          onChange={(values) => onMultiSelectChange('work_mode', values)}
          placeholder="Work Mode"
          labelMap={workModeLabelMap}
          disabled={isMatched && isLoadingFacets}
        />

        <SingleSelect
          options={postedWithinOptions}
          value={currentPostedWithin}
          onChange={(value) => onFilterChange('posted_within', value)}
          placeholder="Date Posted"
        />

        <label className="border-border text-foreground-secondary flex min-h-11 items-center gap-2 rounded-lg border px-3 text-sm">
          <input
            type="checkbox"
            checked={currentSavedOnly}
            disabled={!isAuthenticated}
            onChange={(event) => onFilterChange('saved_only', event.target.checked ? '1' : '')}
            className="h-4 w-4"
          />
          <span>Saved Jobs</span>
          {!isAuthenticated && <span className="text-foreground-muted text-xs">(sign in)</span>}
        </label>
      </div>
    </div>
  );
}
