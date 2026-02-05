"use client";

import { X, MapPin, Building2, ExternalLink, Calendar, Flame, GraduationCap, Globe, Flag } from "lucide-react";
import type { Job } from "../lib/types";

interface JobDetailPanelProps {
  job: Job | null;
  isLoading: boolean;
  onClose: () => void;
}

const categoryLabelMap: Record<string, string> = {
  "software_engineering": "Software Engineering",
  "product_management": "Product Management",
  "data_science_ai": "Data Science & AI",
  "quantitative_finance": "Quantitative Finance",
  "hardware_engineering": "Hardware Engineering",
};

export default function JobDetailPanel({ job, isLoading, onClose }: JobDetailPanelProps) {
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
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-300 border-t-blue-500" />
      </div>
    );
  }

  if (!job) return null;

  return (
    <div className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white dark:border-md-outline-variant dark:bg-md-surface-container-low">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-200 p-6 dark:border-md-outline-variant">
        <div className="flex-1 pr-4">
          <h2 className="text-xl font-bold text-slate-900 dark:text-md-on-surface">{job.title}</h2>
          <div className="mt-2 flex items-center gap-2 text-slate-600 dark:text-md-on-surface-variant">
            <Building2 className="h-4 w-4" />
            <span>{job.company}</span>
            {job.is_faang_plus && (
              <span className="flex items-center gap-1 rounded-full bg-orange-100 px-2 py-0.5 text-xs text-orange-700 dark:bg-orange-900 dark:text-orange-300">
                <Flame className="h-3 w-3" />
                FAANG+
              </span>
            )}
          </div>
          <div className="mt-1 flex items-center gap-2 text-sm text-slate-500 dark:text-md-on-surface-variant">
            <MapPin className="h-4 w-4" />
            <span>{job.location}</span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-md-surface-container dark:hover:text-md-on-surface-variant"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Tags */}
        <div className="flex flex-wrap gap-2">
          {job.job_category && (
            <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-600 dark:bg-md-surface-container dark:text-md-on-surface-variant">
              {categoryLabelMap[job.job_category] || job.job_category}
            </span>
          )}
          {job.visa_sponsored && (
            <span className="flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-700 dark:bg-blue-900 dark:text-blue-300">
              <Globe className="h-3 w-3" />
              Visa Sponsored
            </span>
          )}
          {job.f1_friendly && (
            <span className="flex items-center gap-1 rounded-full bg-green-100 px-3 py-1 text-sm text-green-700 dark:bg-green-900 dark:text-green-300">
              <GraduationCap className="h-3 w-3" />
              F1 Friendly
            </span>
          )}
          {job.requires_us_citizenship && (
            <span className="flex items-center gap-1 rounded-full bg-red-100 px-3 py-1 text-sm text-red-700 dark:bg-red-900 dark:text-red-300">
              <Flag className="h-3 w-3" />
              US Citizenship Required
            </span>
          )}
          {job.requires_advanced_degree && (
            <span className="flex items-center gap-1 rounded-full bg-purple-100 px-3 py-1 text-sm text-purple-700 dark:bg-purple-900 dark:text-purple-300">
              <GraduationCap className="h-3 w-3" />
              Advanced Degree
            </span>
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
              dangerouslySetInnerHTML={{ __html: job.description_text }}
            />
          </div>
        )}
      </div>

      {/* Footer */}
      {job.apply_url && !job.application_closed && (
        <div className="border-t border-slate-200 p-6 dark:border-md-outline-variant">
          <a
            href={job.apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 font-medium text-white transition-colors hover:bg-blue-700"
          >
            Apply Now
            <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      )}
      {job.application_closed && (
        <div className="border-t border-slate-200 p-6 dark:border-md-outline-variant">
          <div className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-200 px-4 py-3 font-medium text-slate-500 dark:bg-md-surface-container-high dark:text-md-on-surface-variant">
            Application Closed
          </div>
        </div>
      )}
    </div>
  );
}
