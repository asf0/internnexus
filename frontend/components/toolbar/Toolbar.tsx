'use client';

import { SlidersHorizontal, Upload, ChevronDown } from 'lucide-react';
import { useEffect } from 'react';
import { Button } from '@/components/ui';
import { useToolbarFilters } from './useToolbarFilters';
import { useToolbarMatch } from './useToolbarMatch';
import { SearchInput } from './SearchInput';
import { FilterPanel } from './FilterPanel';
import { ResumePanel } from './ResumePanel';
import { ActiveFilterSummary, type ActiveFilterItem } from './ActiveFilterSummary';
import { formatCategoryLabel } from '@/lib/utils';
import type { LocationItem } from '@/lib/types/job';

interface ToolbarProps {
  readonly locations: LocationItem[];
  readonly categories?: string[];
  readonly isAuthenticated?: boolean;
}

const jobTypeLabels: Record<string, string> = {
  internship: 'Internship',
  'full-time': 'Full-time',
  'part-time': 'Part-time',
};

const workModeLabels: Record<string, string> = {
  remote: 'Remote',
  hybrid: 'Hybrid',
  'on-site': 'On-site',
};

const postedWithinLabels: Record<string, string> = {
  '24h': 'Past 24 hours',
  '7d': 'Past week',
  '30d': 'Past month',
};

function findLocationLabelOrNull(items: LocationItem[], value: string): string | null {
  for (const item of items) {
    if (item.value === value) return item.label;
    if (item.children) {
      const childLabel = findLocationLabelOrNull(item.children, value);
      if (childLabel) return childLabel;
    }
  }
  return null;
}

function findLocationLabel(items: LocationItem[], value: string): string {
  return findLocationLabelOrNull(items, value) || value;
}

export default function Toolbar({
  locations,
  categories = [],
  isAuthenticated = false,
}: ToolbarProps) {
  const {
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
  } = useToolbarFilters();

  const {
    showResume,
    setShowResume,
    matchResult,
    isMatching,
    facets,
    isLoadingFacets,
    loadFacets,
    handleProfileResumeMatch,
    handleResumeFormSubmit,
    clearMatches,
  } = useToolbarMatch();

  useEffect(() => {
    loadFacets(debouncedFilters, isMatched);
  }, [isMatched, debouncedFilters]);

  const isFiltersActive = showFilters || activeFilterCount > 0;
  const isResumeActive = showResume;
  const matchCount = isMatched ? 1 : 0;
  const withoutValue = (values: string[], value: string) =>
    values.filter((candidate) => candidate !== value);
  const activeFilters: ActiveFilterItem[] = [
    ...currentCompanies.map((value) => ({
      id: `company:${value}`,
      label: `Company: ${value}`,
      onRemove: () => updateMultiSelect('company', withoutValue(currentCompanies, value)),
    })),
    ...currentLocations.map((value) => ({
      id: `location:${value}`,
      label: `Location: ${findLocationLabel(locations, value)}`,
      onRemove: () => updateMultiSelect('location', withoutValue(currentLocations, value)),
    })),
    ...currentCategories.map((value) => ({
      id: `category:${value}`,
      label: `Category: ${formatCategoryLabel(value)}`,
      onRemove: () => updateMultiSelect('category', withoutValue(currentCategories, value)),
    })),
    ...currentJobTypes.map((value) => ({
      id: `job-type:${value}`,
      label: jobTypeLabels[value] || value,
      onRemove: () => updateMultiSelect('job_type', withoutValue(currentJobTypes, value)),
    })),
    ...currentWorkModes.map((value) => ({
      id: `work-mode:${value}`,
      label: workModeLabels[value] || value,
      onRemove: () => updateMultiSelect('work_mode', withoutValue(currentWorkModes, value)),
    })),
    ...(currentPostedWithin
      ? [
          {
            id: `posted:${currentPostedWithin}`,
            label: postedWithinLabels[currentPostedWithin] || currentPostedWithin,
            onRemove: () => updateFilter('posted_within', ''),
          },
        ]
      : []),
    ...(currentSavedOnly
      ? [
          {
            id: 'saved-only',
            label: 'Saved jobs',
            onRemove: () => updateFilter('saved_only', ''),
          },
        ]
      : []),
    ...(isMatched
      ? [
          {
            id: 'matched',
            label: 'Resume matches',
            onRemove: clearMatches,
          },
        ]
      : []),
  ];

  return (
    <div className="bg-canvas/90 sticky top-0 z-50 -mx-4 space-y-3 px-4 py-3 backdrop-blur-md sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
      <div className="relative flex flex-wrap items-center gap-3">
        <SearchInput
          value={searchInput}
          onChange={setSearchInput}
          onSubmit={() => updateFilter('search', searchInput)}
          onClear={() => {
            setSearchInput('');
            updateFilter('search', '');
          }}
          showFilters={showFilters}
        />

        <Button
          variant={isFiltersActive ? 'primary' : 'secondary'}
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2"
        >
          <SlidersHorizontal className="h-4 w-4" />
          <span>Filters</span>
          {activeFilterCount > 0 && (
            <span className="bg-on-accent text-accent flex h-5 w-5 items-center justify-center rounded-full text-xs">
              {activeFilterCount}
            </span>
          )}
          <ChevronDown
            className={`h-4 w-4 transition-transform ${showFilters ? 'rotate-180' : ''}`}
          />
        </Button>

        {isAuthenticated && (
          <Button
            variant={isResumeActive ? 'primary' : 'secondary'}
            onClick={() => setShowResume(!showResume)}
            className="flex items-center gap-2"
          >
            <Upload className="h-4 w-4" />
            <span className="hidden sm:inline">Match Resume</span>
            {matchCount > 0 && (
              <span className="bg-on-accent text-accent rounded-full px-2 py-0.5 text-xs">
                {matchCount}
              </span>
            )}
          </Button>
        )}
      </div>

      {!showFilters && <ActiveFilterSummary items={activeFilters} onClearAll={clearFilters} />}

      <FilterPanel
        isOpen={showFilters}
        isLoadingFacets={isLoadingFacets}
        isMatched={isMatched}
        facets={facets}
        locations={locations}
        categories={categories}
        currentCompanies={currentCompanies}
        currentLocations={currentLocations}
        currentCategories={currentCategories}
        currentJobTypes={currentJobTypes}
        currentWorkModes={currentWorkModes}
        currentPostedWithin={currentPostedWithin}
        currentSavedOnly={currentSavedOnly}
        isAuthenticated={isAuthenticated}
        onMultiSelectChange={updateMultiSelect}
        onFilterChange={updateFilter}
      />

      {isAuthenticated && (
        <ResumePanel
          isOpen={showResume}
          isMatching={isMatching}
          isMatched={isMatched}
          matchResult={matchResult}
          onProfileResumeMatch={handleProfileResumeMatch}
          onResumeFormSubmit={handleResumeFormSubmit}
          onClearMatches={clearMatches}
        />
      )}

      {isPending && <output className="text-foreground-muted text-xs">Updating...</output>}
    </div>
  );
}
