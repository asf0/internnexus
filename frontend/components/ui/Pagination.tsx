"use client";

import Link from "next/link";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  buildPageUrl: (page: number) => string;
}

/**
 * Enhanced Pagination Component
 * 
 * Features:
 * - Page numbers with smart ellipsis
 * - First/Last navigation buttons
 * - Current page highlighting
 * - Responsive design (simplified on mobile)
 * - Accessibility improvements
 * - Disabled state handling
 */
export default function Pagination({ 
  currentPage, 
  totalPages, 
  buildPageUrl 
}: PaginationProps): JSX.Element {
  // Don't render if only one page
  if (totalPages <= 1) return <></>;

  // Generate page numbers to display
  const getPageNumbers = (): (number | string)[] => {
    const pages: (number | string)[] = [];
    
    if (totalPages <= 7) {
      // Show all pages if 7 or fewer
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Smart ellipsis logic
      if (currentPage <= 3) {
        // Near start: show 1 2 3 4 5 ... last
        pages.push(1, 2, 3, 4, 5, '...', totalPages);
      } else if (currentPage >= totalPages - 2) {
        // Near end: show 1 ... last-4 last-3 last-2 last-1 last
        pages.push(1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
      } else {
        // Middle: show 1 ... current-1 current current+1 ... last
        pages.push(1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages);
      }
    }
    
    return pages;
  };

  const pageNumbers = getPageNumbers();

  return (
    <nav 
      role="navigation" 
      aria-label="Pagination"
      className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center"
    >
      <div className="flex items-center gap-1 sm:gap-2">
        {/* First Page */}
        {currentPage > 1 && (
          <Link
            href={buildPageUrl(1)}
            aria-label="Go to first page"
            className="hidden rounded-lg border border-slate-300 bg-white p-2 text-slate-600 hover:bg-slate-50 sm:inline-flex dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Link>
        )}

        {/* Previous Page */}
        {currentPage > 1 ? (
          <Link
            href={buildPageUrl(currentPage - 1)}
            aria-label={`Go to page ${currentPage - 1}`}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
          >
            <span className="flex items-center gap-1">
              <ChevronLeft className="h-4 w-4" />
              <span className="hidden sm:inline">Previous</span>
            </span>
          </Link>
        ) : (
          <span 
            aria-disabled="true"
            className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-400 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant"
          >
            <span className="flex items-center gap-1">
              <ChevronLeft className="h-4 w-4" />
              <span className="hidden sm:inline">Previous</span>
            </span>
          </span>
        )}

        {/* Page Numbers */}
        <div className="flex items-center gap-1">
          {pageNumbers.map((page, index) => {
            if (page === '...') {
              return (
                <span 
                  key={`ellipsis-${index}`}
                  className="px-2 text-slate-400 dark:text-md-on-surface-variant"
                >
                  ...
                </span>
              );
            }

            const pageNum = page as number;
            const isCurrent = pageNum === currentPage;

            return isCurrent ? (
              <span
                key={pageNum}
                aria-current="page"
                aria-label={`Page ${pageNum}, current page`}
                className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white dark:bg-blue-500"
              >
                {pageNum}
              </span>
            ) : (
              <Link
                key={pageNum}
                href={buildPageUrl(pageNum)}
                aria-label={`Go to page ${pageNum}`}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
              >
                {pageNum}
              </Link>
            );
          })}
        </div>

        {/* Next Page */}
        {currentPage < totalPages ? (
          <Link
            href={buildPageUrl(currentPage + 1)}
            aria-label={`Go to page ${currentPage + 1}`}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
          >
            <span className="flex items-center gap-1">
              <span className="hidden sm:inline">Next</span>
              <ChevronRight className="h-4 w-4" />
            </span>
          </Link>
        ) : (
          <span 
            aria-disabled="true"
            className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-400 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant"
          >
            <span className="flex items-center gap-1">
              <span className="hidden sm:inline">Next</span>
              <ChevronRight className="h-4 w-4" />
            </span>
          </span>
        )}

        {/* Last Page */}
        {currentPage < totalPages && (
          <Link
            href={buildPageUrl(totalPages)}
            aria-label="Go to last page"
            className="hidden rounded-lg border border-slate-300 bg-white p-2 text-slate-600 hover:bg-slate-50 sm:inline-flex dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
          >
            <ChevronsRight className="h-4 w-4" />
          </Link>
        )}
      </div>

      {/* Page Info */}
      <span className="text-sm text-slate-500 dark:text-md-on-surface-variant sm:ml-4">
        Page {currentPage} of {totalPages}
      </span>
    </nav>
  );
}
