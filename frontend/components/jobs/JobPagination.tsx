"use client";

import Link from "next/link";

interface JobPaginationProps {
  currentPage: number;
  totalPages: number;
  buildPageUrl: (page: number) => string;
  variant?: "default" | "simple";
}

export function JobPagination({ currentPage, totalPages, buildPageUrl, variant = "default" }: JobPaginationProps) {
  if (totalPages <= 1) return null;

  if (variant === "simple") {
    return (
      <div className="mt-8 flex items-center justify-center gap-2">
        {currentPage > 1 && (
          <Link
            href={buildPageUrl(currentPage - 1)}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
          >
            Previous
          </Link>
        )}

        <span className="px-4 py-2 text-sm text-slate-600 dark:text-md-on-surface-variant">
          Page {currentPage} of {totalPages}
        </span>

        {currentPage < totalPages && (
          <Link
            href={buildPageUrl(currentPage + 1)}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
          >
            Next
          </Link>
        )}
      </div>
    );
  }

  return null;
}
