"use client";

import { X, MapPin, Building2, ExternalLink, Calendar, CheckCircle2, CircleCheck } from "lucide-react";
import DOMPurify from 'isomorphic-dompurify';
import { Badge, LoadingSpinner } from "@/components/ui";
import { JOB_TYPE_LABEL_MAP, WORK_MODE_LABEL_MAP } from "@/lib/constants";
import { formatCategoryLabel } from "@/lib/utils";
import type { Job } from "@/lib/types";

interface JobDetailPanelProps {
  job: Job | null;
  isLoading: boolean;
  onClose: () => void;
  isAuthenticated: boolean;
  onRequireAuthForApply: (applyUrl: string, jobId: string) => void;
  isApplied?: boolean;
  onToggleApplied?: (shouldApply: boolean) => void;
  onApply?: (jobId: string, applyUrl: string) => Promise<void>;
}

export default function JobDetailPanel({
  job,
  isLoading,
  onClose,
  isAuthenticated,
  onRequireAuthForApply,
  isApplied = false,
  onToggleApplied,
  onApply,
}: JobDetailPanelProps) {
  if (!job && !isLoading) {
    return (
      <div className="flex h-full items-center justify-center rounded-2xl border border-slate-200 bg-white p-8 dark:border-md-outline-variant dark:bg-md-surface-container-low">
        <p className="text-slate-500 dark:text-md-on-surface-variant">Select a job to view details</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center rounded-2xl border border-slate-200 bg-white p-8 dark:border-md-outline-variant dark:bg-md-surface-container-low">
        <LoadingSpinner size="md" />
      </div>
    );
  }

  if (!job) return null;

  return (
    <div className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white dark:border-md-outline-variant dark:bg-md-surface-container-low">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-200 p-6 dark:border-md-outline-variant">
        <div className="flex-1 pr-4">
          <h2 id="job-detail-title" className="text-xl font-bold text-slate-900 dark:text-md-on-surface">{job.title}</h2>
          <div className="mt-2 flex items-center gap-2 text-slate-600 dark:text-md-on-surface-variant">
            <Building2 className="h-4 w-4" />
            <span>{job.company}</span>
          </div>
          <div className="mt-1 flex items-center gap-2 text-sm text-slate-500 dark:text-md-on-surface-variant">
            <MapPin className="h-4 w-4" />
            <span>{job.location}</span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-md-surface-container-high dark:hover:text-md-on-surface-variant"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Tags */}
        <div className="flex flex-wrap gap-2">
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

        {/* Posted date */}
        {job.posted_at && (
          <div className="mt-4 flex items-center gap-2 text-sm text-slate-500 dark:text-md-on-surface-variant">
            <Calendar className="h-4 w-4" />
            <span>Posted {new Date(job.posted_at).toLocaleDateString()}</span>
          </div>
        )}

{/* Description */}
         {job.description_text && (
           <div className="mt-6">
             <h3 className="font-semibold text-slate-900 dark:text-md-on-surface">Description</h3>
             <div
               className="mt-2 prose prose-sm prose-slate max-w-none dark:prose-invert text-slate-600 dark:text-md-on-surface-variant"
               dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(job.description_text) }}
             />
           </div>
         )}
      </div>

      {/* Footer */}
      {job.apply_url && (
        <div className="border-t border-slate-200 p-6 dark:border-md-outline-variant">
          {onToggleApplied && (
            <button
              type="button"
              onClick={() => onToggleApplied(!isApplied)}
              className="mb-3 inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-md-outline-variant dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
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
            <button
              type="button"
              onClick={() => onApply?.(job.id, job.apply_url)}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 font-medium text-white transition-colors hover:bg-blue-700"
            >
              Apply Now
              <ExternalLink className="h-4 w-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                if (!job.apply_url) return;
                onRequireAuthForApply(job.apply_url, job.id);
              }}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 font-medium text-white transition-colors hover:bg-blue-700"
            >
              Apply Now
              <ExternalLink className="h-4 w-4" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
