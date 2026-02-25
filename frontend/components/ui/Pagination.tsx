"use client";

import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  buildPageUrl: (page: number) => string;
  totalItems?: number;
  pageSize?: number;
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
      <div className="flex items-center gap-2">
        {currentPage > 1 ? (
          <Link
            href={buildPageUrl(currentPage - 1)}
            aria-label={`Go to page ${currentPage - 1}`}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
          >
            <span className="flex items-center gap-1.5">
              <ChevronLeft className="h-4 w-4" />
              <span>Previous</span>
            </span>
          </Link>
        ) : (
          <span
            aria-disabled="true"
            className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-400 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant"
          >
            <span className="flex items-center gap-1.5">
              <ChevronLeft className="h-4 w-4" />
              <span>Previous</span>
            </span>
          </span>
        )}

        <span className="px-2 text-sm font-medium text-slate-500 dark:text-md-on-surface-variant">
          Page {currentPage} of {totalPages}
        </span>

        {currentPage < totalPages ? (
          <Link
            href={buildPageUrl(currentPage + 1)}
            aria-label={`Go to page ${currentPage + 1}`}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
          >
            <span className="flex items-center gap-1.5">
              <span>Next</span>
              <ChevronRight className="h-4 w-4" />
            </span>
          </Link>
        ) : (
          <span
            aria-disabled="true"
            className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-400 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant"
          >
            <span className="flex items-center gap-1.5">
              <span>Next</span>
              <ChevronRight className="h-4 w-4" />
            </span>
          </span>
        )}
      </div>

      {totalItems && startItem && endItem && (
        <div className="text-sm text-slate-500 dark:text-md-on-surface-variant">
          Showing {startItem}-{endItem} of {totalItems}
        </div>
      )}
    </nav>
  );
}
