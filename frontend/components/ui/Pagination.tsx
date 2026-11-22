'use client';

import Link from 'next/link';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  readonly currentPage: number;
  readonly totalPages: number;
  readonly buildPageUrl: (page: number) => string;
  readonly totalItems?: number;
  readonly pageSize?: number;
}

/**
 * Simplified Pagination Component
 *
 * Features:
 * - Previous/Next navigation
 * - Current page status
 * - Optional item range summary
 * - Cleaner layout for large result sets
 */
export default function Pagination({
  currentPage,
  totalPages,
  buildPageUrl,
  totalItems,
  pageSize = 20,
}: PaginationProps) {
  if (totalPages <= 1) return <></>;

  const startItem = totalItems ? (currentPage - 1) * pageSize + 1 : null;
  const endItem = totalItems ? Math.min(currentPage * pageSize, totalItems) : null;

  return (
    <nav
      role="navigation"
      aria-label="Pagination"
      className="mt-8 flex flex-col items-center gap-3"
    >
      <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2">
        {currentPage > 1 && (
          <Link
            href={buildPageUrl(currentPage - 1)}
            aria-label={`Go to page ${currentPage - 1}`}
            className="border-border bg-surface text-foreground-secondary hover:bg-surface-subtle focus-visible:ring-focus-ring col-start-1 justify-self-end rounded-lg border px-3 py-2 text-sm font-medium focus-visible:ring-2 focus-visible:outline-none"
          >
            <span className="flex items-center gap-1.5">
              <ChevronLeft className="h-4 w-4" />
              <span>Previous</span>
            </span>
          </Link>
        )}

        <span className="text-foreground-muted col-start-2 px-2 text-sm font-medium whitespace-nowrap">
          Page {currentPage}
        </span>

        {currentPage < totalPages && (
          <Link
            href={buildPageUrl(currentPage + 1)}
            aria-label={`Go to page ${currentPage + 1}`}
            className="border-border bg-surface text-foreground-secondary hover:bg-surface-subtle focus-visible:ring-focus-ring col-start-3 justify-self-start rounded-lg border px-3 py-2 text-sm font-medium focus-visible:ring-2 focus-visible:outline-none"
          >
            <span className="flex items-center gap-1.5">
              <span>Next</span>
              <ChevronRight className="h-4 w-4" />
            </span>
          </Link>
        )}
      </div>

      {totalItems && startItem && endItem && (
        <div className="text-foreground-muted text-sm">
          Showing {startItem}-{endItem} of {totalItems}
        </div>
      )}
    </nav>
  );
}
