"use client";

import { MapPin, Building2, TrendingUp, Bookmark, BookmarkCheck, CircleCheck, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui";
import { JOB_TYPE_LABEL_MAP, WORK_MODE_LABEL_MAP } from "@/lib/constants";
import { getMatchColor, formatCategoryLabel } from "@/lib/utils";
import type { Job } from "@/lib/types/job";

interface JobCardProps {
  job: Job;
  isSelected: boolean;
  matchPercentage?: number;
  onClick: () => void;
  isSaved?: boolean;
  onToggleSave?: (shouldSave: boolean) => void;
  isApplied?: boolean;
  onToggleApplied?: (shouldApply: boolean) => void;
}

export function JobCard({
  job,
  isSelected,
  matchPercentage,
  onClick,
  isSaved = false,
  onToggleSave,
  isApplied = false,
  onToggleApplied,
}: JobCardProps) {
  return (
    <article
      onClick={onClick}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onClick();
        }
      }}
      tabIndex={0}
      className={`mb-3 cursor-pointer rounded-2xl border p-5 transition-all hover:shadow-md ${
        isSelected
          ? "border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-950"
          : "border-slate-200 bg-white hover:border-slate-300 dark:border-md-outline-variant dark:bg-md-surface-container-low dark:hover:border-slate-600"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-md-on-surface">{job.title}</h3>
            {matchPercentage !== undefined && (
              <span className={`flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${getMatchColor(matchPercentage)}`}>
                <TrendingUp className="h-3 w-3" />
                {matchPercentage.toFixed(1)}%
              </span>
            )}
          </div>
          <div className="mt-1 flex items-center gap-3 text-sm text-slate-600 dark:text-md-on-surface-variant">
            <span className="flex items-center gap-1">
              <Building2 className="h-4 w-4" />
              {job.company}
            </span>
            <span className="flex items-center gap-1">
              <MapPin className="h-4 w-4" />
              {job.location}
            </span>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {job.job_category && (
              <Badge variant="default">
                {formatCategoryLabel(job.job_category)}
              </Badge>
            )}
            {job.job_type && (
              <Badge variant="info">
                {JOB_TYPE_LABEL_MAP[job.job_type] || job.job_type}
              </Badge>
            )}
            {job.work_mode && (
              <Badge variant="success">
                {WORK_MODE_LABEL_MAP[job.work_mode] || job.work_mode}
              </Badge>
            )}
          </div>
        </div>
        <div className="ml-3 flex items-center gap-2">
          {onToggleApplied && (
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onToggleApplied(!isApplied);
              }}
              className="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white p-2 text-slate-600 hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant"
              aria-label={isApplied ? "Mark as not applied" : "Mark as applied"}
              title={isApplied ? "Mark as not applied" : "Mark as applied"}
            >
              {isApplied ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              ) : (
                <CircleCheck className="h-4 w-4" />
              )}
            </button>
          )}
          {onToggleSave && (
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onToggleSave(!isSaved);
              }}
              className="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white p-2 text-slate-600 hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant"
              aria-label={isSaved ? "Unsave job" : "Save job"}
              title={isSaved ? "Unsave job" : "Save job"}
            >
              {isSaved ? (
                <BookmarkCheck className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              ) : (
                <Bookmark className="h-4 w-4" />
              )}
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
