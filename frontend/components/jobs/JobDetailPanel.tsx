'use client';

import { X, ExternalLink, CheckCircle2, CircleCheck } from 'lucide-react';
import { Badge, Button, LoadingSpinner } from '@/components/ui';
import { JOB_TYPE_LABEL_MAP, WORK_MODE_LABEL_MAP } from '@/lib/constants';
import { formatCategoryLabel } from '@/lib/utils';
import type { JobSummary } from '@/lib/types';
import type { JobDetailView } from './fetchJobDetail';

interface JobDetailPanelProps {
  readonly job: JobSummary | null;
  readonly detail: JobDetailView | null;
  readonly isLoading: boolean;
  readonly error: string | null;
  readonly isUnavailable: boolean;
  readonly onRetry: () => void;
  readonly onClose: () => void;
  readonly isAuthenticated: boolean;
  readonly onRequireAuthForApply: (applyUrl: string, jobId: string) => void;
  readonly isApplied?: boolean;
  readonly isAppliedPending?: boolean;
  readonly onToggleApplied?: (shouldApply: boolean) => void;
  readonly onApply?: (jobId: string, applyUrl: string) => Promise<void>;
}

export default function JobDetailPanel({
  job,
  detail,
  isLoading,
  error,
  isUnavailable,
  onRetry,
  onClose,
  isAuthenticated,
  onRequireAuthForApply,
  isApplied = false,
  isAppliedPending = false,
  onToggleApplied,
  onApply,
}: JobDetailPanelProps) {
  if (!job && !isLoading) {
    return (
      <div className="border-border bg-surface flex h-full items-center justify-center rounded-2xl border p-8">
        <p className="text-foreground-muted">Select a job to view details</p>
      </div>
    );
  }

  if (!job) return null;

  return (
    <div className="border-border bg-surface flex h-full flex-col rounded-2xl border">
      {/* Header */}
      <div className="border-border flex items-start justify-between border-b p-6">
        <div className="flex-1 pr-4">
          <h2 id="job-detail-title" className="text-foreground text-xl font-bold">
            {job.title}
          </h2>
          <div className="text-foreground-secondary mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
            <span>{job.company}</span>
            <span aria-hidden="true">·</span>
            <span>{job.location}</span>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close job details"
          className="text-foreground-muted hover:bg-surface-subtle hover:text-foreground focus-visible:ring-focus-ring rounded-lg p-2 focus-visible:ring-2 focus-visible:outline-none"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Tags */}
        <div className="flex flex-wrap gap-2">
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

        {/* Posted date */}
        {job.posted_at && (
          <time dateTime={job.posted_at} className="text-foreground-muted mt-4 block text-sm">
            Posted{' '}
            {new Date(job.posted_at).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            })}
          </time>
        )}

        {isLoading && (
          <div
            className="text-foreground-muted flex min-h-48 items-center justify-center gap-3"
            aria-live="polite"
          >
            <LoadingSpinner size="md" />
            <span>Loading job description...</span>
          </div>
        )}

        {!isLoading && error && (
          <div className="border-border bg-surface-subtle mt-6 rounded-xl border p-5" role="alert">
            <p className="text-foreground-secondary text-sm">{error}</p>
            <Button type="button" variant="secondary" size="sm" onClick={onRetry} className="mt-4">
              Try again
            </Button>
          </div>
        )}

        {!isLoading && !error && detail?.description_html && (
          <div className="mt-6">
            <h3 className="text-foreground font-semibold">Description</h3>
            <div
              className="prose prose-sm prose-slate dark:prose-invert text-foreground-secondary mt-2 max-w-none"
              dangerouslySetInnerHTML={{ __html: detail.description_html }}
            />
          </div>
        )}
      </div>

      {/* Footer */}
      {job.apply_url && !isUnavailable && (
        <div className="border-border border-t p-6">
          {onToggleApplied && (
            <button
              type="button"
              onClick={() => onToggleApplied(!isApplied)}
              disabled={isAppliedPending}
              aria-busy={isAppliedPending}
              className="border-border text-foreground-secondary hover:bg-surface-subtle mb-3 inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm disabled:cursor-wait disabled:opacity-50"
            >
              {isApplied ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  Applied
                </>
              ) : (
                <>
                  <CircleCheck className="h-4 w-4" />
                  Mark as applied
                </>
              )}
            </button>
          )}
          {isAuthenticated ? (
            <Button
              type="button"
              size="lg"
              onClick={() => onApply?.(job.id, job.apply_url)}
              className="w-full"
            >
              Apply Now
              <ExternalLink className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="button"
              size="lg"
              onClick={() => {
                if (!job.apply_url) return;
                onRequireAuthForApply(job.apply_url, job.id);
              }}
              className="w-full"
            >
              Apply Now
              <ExternalLink className="h-4 w-4" />
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
