"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { MapPin, Building2, Flame } from "lucide-react";
import JobDetailPanel from "./JobDetailPanel";
import type { Job } from "../lib/types";

interface JobListProps {
  jobs: Job[];
  total: number;
  totalPages: number;
  currentPage: number;
}

const categoryLabelMap: Record<string, string> = {
  "software_engineering": "Software Engineering",
  "product_management": "Product Management",
  "data_science_ai": "Data Science & AI",
  "quantitative_finance": "Quantitative Finance",
  "hardware_engineering": "Hardware Engineering",
};

export default function JobList({ jobs, total, totalPages, currentPage }: JobListProps) {
  const searchParams = useSearchParams();
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  const handleJobClick = (job: Job) => {
    setSelectedJob(job);
  };

  const handleClose = () => {
    setSelectedJob(null);
  };

  const buildPageUrl = (page: number) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", page.toString());
    return `/?${params.toString()}`;
  };

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold dark:text-slate-100">Latest roles</h2>
        <span className="text-sm text-slate-500 dark:text-slate-400">{total} openings</span>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        {/* Job List - Full width on mobile, half width on desktop with detail panel */}
        <div className={`transition-all duration-300 ${selectedJob ? "w-full lg:w-1/2" : "w-full"}`}>
          {jobs.map((job) => (
            <article 
              key={job.id} 
              onClick={() => handleJobClick(job)}
              className={`mb-3 cursor-pointer rounded-2xl border p-5 transition-all hover:shadow-md ${
                selectedJob?.id === job.id
                  ? "border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-950"
                  : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-600"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{job.title}</h3>
                    {job.is_faang_plus && (
                      <Flame className="h-4 w-4 text-orange-500" />
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400">
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
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                        {categoryLabelMap[job.job_category] || job.job_category}
                      </span>
                    )}
                    {job.visa_sponsored && (
                      <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                        Visa
                      </span>
                    )}
                    {job.f1_friendly && (
                      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700 dark:bg-green-900 dark:text-green-300">
                        F1
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </article>
          ))}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              {currentPage > 1 && (
                <Link
                  href={buildPageUrl(currentPage - 1)}
                  className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  Previous
                </Link>
              )}
              
              <span className="px-4 py-2 text-sm text-slate-600 dark:text-slate-400">
                Page {currentPage} of {totalPages}
              </span>
              
              {currentPage < totalPages && (
                <Link
                  href={buildPageUrl(currentPage + 1)}
                  className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  Next
                </Link>
              )}
            </div>
          )}
        </div>

        {/* Detail Panel - Fullscreen modal on mobile, side panel on desktop */}
        {selectedJob && (
          <>
            {/* Mobile: Full-screen modal overlay */}
            <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={handleClose} />
            <div className="fixed inset-4 z-50 flex lg:hidden">
              <div className="w-full rounded-2xl bg-white dark:bg-slate-900">
                <JobDetailPanel
                  job={selectedJob}
                  isLoading={false}
                  onClose={handleClose}
                />
              </div>
            </div>

            {/* Desktop: Sticky side panel */}
            <div className="hidden sticky top-4 h-[calc(100vh-6rem)] w-1/2 min-w-[400px] lg:block">
              <JobDetailPanel
                job={selectedJob}
                isLoading={false}
                onClose={handleClose}
              />
            </div>
          </>
        )}
      </div>
    </section>
  );
}
