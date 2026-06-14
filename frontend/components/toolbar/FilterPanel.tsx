'use client';

import { MultiSelect, LocationSelect } from '@/components/common';
import { SingleSelect } from '@/components/ui';
import { formatCategoryLabel } from '@/lib/utils';
import type { MatchFacetsResponse, LocationItem } from '@/lib/types/job';

interface FilterPanelProps {
  readonly isOpen: boolean;
  readonly isLoadingFacets: boolean;
  readonly isMatched: boolean;
  readonly facets: MatchFacetsResponse | null;
  readonly companies: string[];
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
  companies,
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
  if (!isOpen) return null;

  return (
    <div className="dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900">
      {isLoadingFacets && (
        <div className="dark:text-md-on-surface-variant mb-2 text-xs text-slate-500">
          Loading filter options...
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <MultiSelect
          options={
            isMatched && facets
              ? facets.companies.map((f) => f.value).sort((a, b) => a.localeCompare(b))
              : [...companies].sort((a, b) => a.localeCompare(b))
          }
          selected={currentCompanies}
          onChange={(values) => onMultiSelectChange('company', values)}
          placeholder="Company"
          disabled={isMatched && isLoadingFacets}
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

        <label className="dark:border-md-outline dark:text-md-on-surface-variant flex min-h-[44px] items-center gap-2 rounded-lg border border-slate-300 px-3 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={currentSavedOnly}
            disabled={!isAuthenticated}
            onChange={(event) => onFilterChange('saved_only', event.target.checked ? '1' : '')}
            className="h-4 w-4"
          />
          <span>Saved Jobs</span>
          {!isAuthenticated && <span className="text-xs text-slate-500">(sign in)</span>}
        </label>
      </div>
    </div>
  );
}
