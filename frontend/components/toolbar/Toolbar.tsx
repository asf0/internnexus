'use client';

import { SlidersHorizontal, Upload, ChevronDown, X } from 'lucide-react';
import { useEffect } from 'react';
import { Button } from '@/components/ui';
import { useToolbarFilters } from './useToolbarFilters';
import { useToolbarMatch } from './useToolbarMatch';
import { SearchInput } from './SearchInput';
import { FilterPanel } from './FilterPanel';
import { ResumePanel } from './ResumePanel';
import type { LocationItem } from '@/lib/types/job';

interface ToolbarProps {
  readonly companies: string[];
  readonly locations: LocationItem[];
  readonly categories?: string[];
  readonly isAuthenticated?: boolean;
}

export default function Toolbar({
  companies,
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

  return (
    <div className="dark:bg-md-surface/80 sticky top-0 z-50 -mx-4 space-y-3 bg-white/80 px-4 py-2 backdrop-blur-md sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
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
            <span className="bg-md-primary flex h-5 w-5 items-center justify-center rounded-full text-xs text-white">
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
              <span className="bg-md-primary rounded-full px-2 py-0.5 text-xs text-white">
                {matchCount}
              </span>
            )}
          </Button>
        )}

        {activeFilterCount > 0 && (
          <Button variant="ghost" onClick={clearFilters} className="flex items-center gap-1">
            <X className="h-4 w-4" />
            <span className="hidden sm:inline">Clear</span>
          </Button>
        )}
      </div>

      <FilterPanel
        isOpen={showFilters}
        isLoadingFacets={isLoadingFacets}
        isMatched={isMatched}
        facets={facets}
        companies={companies}
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

      {isPending && (
        <div className="dark:text-md-on-surface-variant text-xs text-slate-500">Updating...</div>
      )}
    </div>
  );
}
