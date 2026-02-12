"use client";

import { useState, useEffect, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { MapPin, Building2, Flame, TrendingUp } from "lucide-react";
import JobDetailPanel from "./JobDetailPanel";
import { fetchMatchedJobs } from "../app/actions/match";
import { Badge } from "./ui";
import type { Job } from "../lib/types";

interface MatchedJobListProps {
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

const getMatchColor = (percentage: number) => {
  if (percentage >= 80) return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
  if (percentage >= 60) return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300";
  if (percentage >= 40) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300";
  return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
};

const PAGE_SIZE = 20;

export default function MatchedJobList({ totalPages: _totalPages, currentPage }: MatchedJobListProps) {
  const searchParams = useSearchParams();
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [matchScoresMap, setMatchScoresMap] = useState<Map<string, number>>(new Map());
  const [isLoading, setIsLoading] = useState(true);
  const [total, setTotal] = useState(0);

  // Load match data from localStorage and fetch jobs
  useEffect(() => {
    const loadMatchedJobs = async () => {
      setIsLoading(true);
      try {
        const storedIds = localStorage.getItem("matchIds");
        const storedScores = localStorage.getItem("matchScores");
        
        if (!storedIds) {
          setJobs([]);
          setTotal(0);
          return;
        }

        const matchIds: string[] = JSON.parse(storedIds);
        const scores: Record<string, number> = storedScores ? JSON.parse(storedScores) : {};
        
        setMatchScoresMap(new Map(Object.entries(scores)));
        setTotal(matchIds.length);

        // Paginate the match IDs
        const startIdx = (currentPage - 1) * PAGE_SIZE;
        const endIdx = startIdx + PAGE_SIZE;
        const pageIds = matchIds.slice(startIdx, endIdx);

        if (pageIds.length === 0) {
          setJobs([]);
          return;
        }

        // Fetch the jobs for this page using server action
        const data = await fetchMatchedJobs(pageIds, PAGE_SIZE);
        
        // Sort jobs by their position in pageIds (which preserves match ranking)
        const idOrder = new Map(pageIds.map((id, idx) => [id, idx]));
        const sortedJobs = [...data.items].sort(
          (a: Job, b: Job) => (idOrder.get(a.id) ?? Infinity) - (idOrder.get(b.id) ?? Infinity)
        );
        setJobs(sortedJobs);
      } catch (error) {
        console.error("Failed to load matched jobs:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadMatchedJobs();
  }, [currentPage]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

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

  if (isLoading) {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold dark:text-md-on-surface">Matched roles</h2>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-300 border-t-blue-500" />
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold dark:text-md-on-surface">Matched roles</h2>
        <span className="text-sm text-slate-500 dark:text-md-on-surface-variant">{total} matches</span>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        {/* Job List */}
        <div className={`transition-all duration-300 ${selectedJob ? "w-full lg:w-1/2" : "w-full"}`}>
          {jobs.map((job) => {
            const matchPercentage = matchScoresMap.get(job.id);
            return (
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
                          {categoryLabelMap[job.job_category] || job.job_category}
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
          })}

          {jobs.length === 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center dark:border-md-outline-variant dark:bg-md-surface-container-low">
              <p className="text-slate-500 dark:text-md-on-surface-variant">No matched jobs found.</p>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
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
          )}
        </div>

        {/* Detail Panel */}
        {selectedJob && (
          <>
            {/* Mobile: Full-screen modal overlay */}
            <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={handleClose} />
            <div className="fixed inset-4 z-50 flex lg:hidden">
              <div className="w-full rounded-2xl bg-white dark:bg-md-surface-container-low">
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
