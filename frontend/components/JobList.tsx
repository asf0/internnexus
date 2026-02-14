"use client";

import { useMemo, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { MapPin, Building2, Flame } from "lucide-react";
import { JobDetailPanelContainer } from "./JobDetailPanelContainer";
import Pagination from "./ui/Pagination";
import { Badge } from "./ui";
import { CATEGORY_LABEL_MAP } from "../lib/constants";
import { generateJobSlug, findJobBySlug } from "../lib/utils";
import type { Job } from "../lib/types";

interface JobListProps {
  jobs: Job[];
  total: number;
  totalPages: number;
  currentPage: number;
}

export default function JobList({ jobs, total, totalPages, currentPage }: JobListProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const selectedSlug = searchParams.get("selected");

  const selectedJob = useMemo(() => {
    if (!selectedSlug) return null;
    return findJobBySlug(jobs, selectedSlug) || null;
  }, [selectedSlug, jobs]);

  const handleJobClick = useCallback(
    (job: Job) => {
      const slug = generateJobSlug(job.title, job.company, job.id);
      const params = new URLSearchParams(searchParams.toString());
      params.set("selected", slug);
      router.push(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [searchParams, router, pathname]
  );

  const handleClose = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("selected");
    const newUrl = params.toString() ? `${pathname}?${params.toString()}` : pathname;
    router.push(newUrl, { scroll: false });
  }, [searchParams, router, pathname]);

  const buildPageUrl = (page: number) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", page.toString());
    params.delete("selected");
    return `/?${params.toString()}`;
  };

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold dark:text-md-on-surface">Latest roles</h2>
        <span className="text-sm text-slate-500 dark:text-md-on-surface-variant">{total} openings</span>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        <div className={`transition-all duration-300 ${selectedJob ? "w-full lg:w-1/2" : "w-full"}`}>
          {jobs.map((job) => (
            <article
              key={job.id}
              onClick={() => handleJobClick(job)}
              className={`mb-3 cursor-pointer rounded-2xl border p-5 transition-all hover:shadow-md ${
                selectedJob?.id === job.id
                  ? "border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-950"
                  : "border-slate-200 bg-white hover:border-slate-300 dark:border-md-outline-variant dark:bg-md-surface-container-low dark:hover:border-slate-600"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-md-on-surface">{job.title}</h3>
                    {job.is_faang_plus && (
                      <Flame className="h-4 w-4 text-orange-500" />
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
          ))}

          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            buildPageUrl={buildPageUrl}
          />
        </div>

        {selectedSlug && (
          <JobDetailPanelContainer
            job={selectedJob}
            onClose={handleClose}
          />
        )}
      </div>
    </section>
  );
}
