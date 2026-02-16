"use client";

import { MapPin, Building2, Flame, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui";
import { CATEGORY_LABEL_MAP } from "@/lib/constants";
import { getMatchColor } from "@/lib/utils";
import type { Job } from "@/lib/types/job";

interface JobCardProps {
  job: Job;
  isSelected: boolean;
  matchPercentage?: number;
  onClick: () => void;
}

export function JobCard({ job, isSelected, matchPercentage, onClick }: JobCardProps) {
  return (
    <article
      onClick={onClick}
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
            {job.is_faang_plus && (
              <Flame className="h-4 w-4 text-orange-500" />
            )}
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
                {CATEGORY_LABEL_MAP[job.job_category] || job.job_category}
              </Badge>
            )}
            {job.visa_sponsored && (
              <Badge variant="visa">Visa</Badge>
            )}
            {job.f1_friendly && (
              <Badge variant="f1">F1</Badge>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
