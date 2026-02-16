"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { JobDetailPanelContainer } from "./JobDetailPanelContainer";
import { JobCard } from "./JobCard";
import Pagination from "@/components/ui/Pagination";
import { LoadingSpinner } from "@/components/ui";
import { fetchMatchedJobs } from "@/app/actions/jobs";
import { LOCAL_STORAGE_KEYS, DEFAULT_PAGE_SIZE } from "@/lib/constants";
import { generateJobSlug, findJobBySlug } from "@/lib/utils";
import type { Job } from "@/lib/types/job";

interface JobListProps {
  jobs?: Job[];
  total?: number;
  totalPages?: number;
  currentPage: number;
  matched?: boolean;
}

export default function JobList({
  jobs: serverJobs,
  total: serverTotal,
  totalPages: serverTotalPages,
  currentPage,
  matched = false,
}: JobListProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [clientJobs, setClientJobs] = useState<Job[]>([]);
  const [matchScoresMap, setMatchScoresMap] = useState<Map<string, number>>(new Map());
  const [isLoading, setIsLoading] = useState(matched);
  const [clientTotal, setClientTotal] = useState(0);

  const selectedSlug = searchParams.get("selected");
  const searchQuery = searchParams.get("search") || "";
  const company = searchParams.get("company") || "";
  const location = searchParams.get("location") || "";
  const category = searchParams.get("category") || "";
  const visaSponsored = searchParams.get("visa_sponsored");
  const f1Friendly = searchParams.get("f1_friendly");
  const jobType = searchParams.get("job_type") || "";
  const workMode = searchParams.get("work_mode") || "";
  const postedWithin = searchParams.get("posted_within") || "";

  const jobs = matched ? clientJobs : (serverJobs || []);
  const total = matched ? clientTotal : (serverTotal || 0);
  const totalPagesComputed = matched ? Math.ceil(clientTotal / DEFAULT_PAGE_SIZE) : (serverTotalPages || 1);

  const selectedJob = useMemo(() => {
    if (!selectedSlug) return null;
    return findJobBySlug(jobs, selectedSlug) || null;
  }, [selectedSlug, jobs]);

  useEffect(() => {
    if (!matched) return;

    const loadMatchedJobs = async () => {
      setIsLoading(true);
      try {
        const storedIds = localStorage.getItem(LOCAL_STORAGE_KEYS.MATCH_IDS);
        const storedScores = localStorage.getItem(LOCAL_STORAGE_KEYS.MATCH_SCORES);

        if (!storedIds) {
          setClientJobs([]);
          setClientTotal(0);
          return;
        }

        const matchIds: string[] = JSON.parse(storedIds);
        const scores: Record<string, number> = storedScores ? JSON.parse(storedScores) : {};

        setMatchScoresMap(new Map(Object.entries(scores)));

        if (matchIds.length === 0) {
          setClientJobs([]);
          setClientTotal(0);
          return;
        }

        const data = await fetchMatchedJobs({
          page: currentPage,
          page_size: DEFAULT_PAGE_SIZE,
          search: searchQuery,
          company,
          location,
          category,
          visa_sponsored: visaSponsored || undefined,
          f1_friendly: f1Friendly || undefined,
          job_type: jobType,
          work_mode: workMode,
          posted_within: postedWithin,
          match_ids: matchIds.join("|"),
        });

        if ("error" in data) {
          if (process.env.NODE_ENV !== "production") {
            console.error("Failed to load matched jobs:", data.error);
          }
          setClientJobs([]);
          setClientTotal(0);
        } else {
          setClientJobs(data.items);
          setClientTotal(data.total);
        }
      } catch (error) {
        if (process.env.NODE_ENV !== "production") {
          console.error("Failed to load matched jobs:", error);
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadMatchedJobs();
  }, [
    matched,
    currentPage,
    searchQuery,
    company,
    location,
    category,
    visaSponsored,
    f1Friendly,
    jobType,
    workMode,
    postedWithin,
  ]);

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

  if (isLoading) {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold dark:text-md-on-surface">
            {matched ? "Matched roles" : "Latest roles"}
          </h2>
        </div>
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="md" />
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold dark:text-md-on-surface">
          {matched ? "Matched roles" : "Latest roles"}
        </h2>
        <span className="text-sm text-slate-500 dark:text-md-on-surface-variant">
          {total} {matched ? "matches" : "openings"}
        </span>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        <div className={`transition-all duration-300 ${selectedJob ? "w-full lg:w-1/2" : "w-full"}`}>
          {jobs.map((job) => {
            const matchPercentage = matched ? matchScoresMap.get(job.id) : undefined;
            return (
              <JobCard
                key={job.id}
                job={job}
                isSelected={selectedJob?.id === job.id}
                matchPercentage={matchPercentage}
                onClick={() => handleJobClick(job)}
              />
            );
          })}

          {jobs.length === 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center dark:border-md-outline-variant dark:bg-md-surface-container-low">
              <p className="text-slate-500 dark:text-md-on-surface-variant">
                {matched ? "No matched jobs found." : "No jobs found."}
              </p>
            </div>
          )}

          {matched && totalPagesComputed > 1 ? (
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
                Page {currentPage} of {totalPagesComputed}
              </span>

              {currentPage < totalPagesComputed && (
                <Link
                  href={buildPageUrl(currentPage + 1)}
                  className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
                >
                  Next
                </Link>
              )}
            </div>
          ) : !matched && totalPagesComputed > 1 ? (
            <Pagination
              currentPage={currentPage}
              totalPages={totalPagesComputed}
              buildPageUrl={buildPageUrl}
            />
          ) : null}
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
