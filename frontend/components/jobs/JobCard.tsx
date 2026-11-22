'use client';

import Link from 'next/link';
import { Bookmark, BookmarkCheck, CircleCheck, CheckCircle2 } from 'lucide-react';
import { Badge, IconButton } from '@/components/ui';
import { JOB_TYPE_LABEL_MAP, WORK_MODE_LABEL_MAP } from '@/lib/constants';
import { getMatchColor, formatCategoryLabel, isJobNew } from '@/lib/utils';
import type { JobSummary } from '@/lib/types/job';

interface JobCardProps {
  readonly job: JobSummary;
  readonly isSelected: boolean;
  readonly matchPercentage?: number;
  readonly onClick: () => void;
  readonly isSaved?: boolean;
  readonly onToggleSave?: (shouldSave: boolean) => void;
  readonly isSavePending?: boolean;
  readonly isApplied?: boolean;
  readonly onToggleApplied?: (shouldApply: boolean) => void;
  readonly isAppliedPending?: boolean;
}

export function JobCard({
  job,
  isSelected,
  matchPercentage,
  onClick,
  isSaved = false,
  onToggleSave,
  isSavePending = false,
  isApplied = false,
  onToggleApplied,
  isAppliedPending = false,
}: JobCardProps) {
  return (
    <article
      aria-label={`${job.title} at ${job.company}`}
      className={`relative mb-3 rounded-xl border p-5 transition-colors ${
        isSelected
          ? 'border-accent bg-surface-raised ring-accent ring-1'
          : 'border-border bg-surface hover:border-accent/60'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-semibold">
              <Link
                href={`/jobs/${job.id}`}
                prefetch={false}
                aria-expanded={isSelected}
                onClick={(event) => {
                  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
                    event.stopPropagation();
                    return;
                  }
                  event.preventDefault();
                  event.stopPropagation();
                  onClick();
                }}
                className="text-foreground focus-visible:ring-focus-ring underline-offset-4 after:absolute after:inset-0 after:content-[''] hover:underline focus-visible:rounded-sm focus-visible:ring-2 focus-visible:outline-none"
              >
                {job.title}
              </Link>
            </h3>
            {matchPercentage !== undefined && (
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${getMatchColor(matchPercentage)}`}
              >
                {matchPercentage.toFixed(0)}% match
              </span>
            )}
          </div>
          <div className="text-foreground-secondary mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
            <span>{job.company}</span>
            <span aria-hidden="true">·</span>
            <span>{job.location}</span>
            {job.posted_at && (
              <>
                <span aria-hidden="true">·</span>
                <time dateTime={job.posted_at}>
                  Posted{' '}
                  {new Date(job.posted_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </time>
              </>
            )}
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {job.posted_at && isJobNew(job.posted_at) && <Badge variant="success">New</Badge>}
            {job.job_category && (
              <Badge variant="outline">{formatCategoryLabel(job.job_category)}</Badge>
            )}
            {job.job_type && (
              <Badge variant="outline">{JOB_TYPE_LABEL_MAP[job.job_type] || job.job_type}</Badge>
            )}
            {job.work_mode && (
              <Badge variant="outline">{WORK_MODE_LABEL_MAP[job.work_mode] || job.work_mode}</Badge>
            )}
          </div>
        </div>
        <div className="relative z-10 ml-3 flex items-center gap-2">
          {onToggleApplied && (
            <IconButton
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onToggleApplied(!isApplied);
              }}
              disabled={isAppliedPending}
              label={isApplied ? 'Mark as not applied' : 'Mark as applied'}
              aria-busy={isAppliedPending}
            >
              {isApplied ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              ) : (
                <CircleCheck className="h-4 w-4" />
              )}
            </IconButton>
          )}
          {onToggleSave && (
            <IconButton
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onToggleSave(!isSaved);
              }}
              disabled={isSavePending}
              label={isSaved ? 'Unsave job' : 'Save job'}
              aria-busy={isSavePending}
            >
              {isSaved ? (
                <BookmarkCheck className="text-accent h-4 w-4" />
              ) : (
                <Bookmark className="h-4 w-4" />
              )}
            </IconButton>
          )}
        </div>
      </div>
    </article>
  );
}
