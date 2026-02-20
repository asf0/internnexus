"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { JobDetailPanelContainer } from "./JobDetailPanelContainer";
import { JobCard } from "./JobCard";
import { AuthModal } from "@/components/auth";
import Pagination from "@/components/ui/Pagination";
import { LoadingSpinner, Toast } from "@/components/ui";
import { fetchMatchPage } from "@/app/actions/match";
import { fetchJobs } from "@/lib/api";
import { useMatchState } from "@/lib/hooks/useMatchState";
import { LOCAL_STORAGE_KEYS, SESSION_STORAGE_KEYS, DEFAULT_PAGE_SIZE } from "@/lib/constants";
import { SHOW_JOB_COUNT } from "@/lib/config";
import { generateJobSlug, findJobBySlug } from "@/lib/utils";
import type { Job } from "@/lib/types/job";

interface JobListProps {
  jobs?: Job[];
  total?: number;
  totalPages?: number;
  currentPage: number;
  matched?: boolean;
  isAuthenticated?: boolean;
}

export default function JobList({
  jobs: serverJobs,
  total: serverTotal,
  totalPages: serverTotalPages,
  currentPage,
  matched = false,
  isAuthenticated = false,
}: JobListProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const { sessionId, matchScores: matchScoresMap, clearMatches, isLoading: isMatchStateLoading } = useMatchState();

  const [clientJobs, setClientJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(matched);
  const [clientTotal, setClientTotal] = useState(0);
  const [appendedJobs, setAppendedJobs] = useState<Job[]>([]);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [lastLoadedPage, setLastLoadedPage] = useState(currentPage);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [pendingApplyUrl, setPendingApplyUrl] = useState<string | null>(null);
  const [showPopupBlockedToast, setShowPopupBlockedToast] = useState(false);

  const selectedSlug = searchParams.get("selected");
  const searchQuery = searchParams.get("search") || "";
  const company = searchParams.get("company") || "";
  const location = searchParams.get("location") || "";
  const category = searchParams.get("category") || "";
  const jobType = searchParams.get("job_type") || "";
  const workMode = searchParams.get("work_mode") || "";
  const postedWithin = searchParams.get("posted_within") || "";

  const jobs = matched ? clientJobs : [...(serverJobs || []), ...appendedJobs];
  const total = matched ? clientTotal : (serverTotal || 0);
  const totalPagesComputed = matched ? Math.ceil(clientTotal / DEFAULT_PAGE_SIZE) : (serverTotalPages || 1);

  const selectedJob = useMemo(() => {
    if (!selectedSlug) return null;
    return findJobBySlug(jobs, selectedSlug) || null;
  }, [selectedSlug, jobs]);

  useEffect(() => {
    if (!matched) return;
    if (isMatchStateLoading) return; // Wait for match state to load from localStorage

    const loadMatchedJobs = async () => {
      setIsLoading(true);
      try {
        if (!sessionId) {
          setClientJobs([]);
          setClientTotal(0);
          return;
        }

        const data = await fetchMatchPage(
          sessionId,
          currentPage,
          DEFAULT_PAGE_SIZE,
          {
            search: searchQuery,
            company,
            location,
            category,
            job_type: jobType,
            work_mode: workMode,
            posted_within: postedWithin,
          }
        );

        if (data.error) {
          // Handle error - especially 404 (session expired)
          if (data.error.includes("session expired")) {
            // Clear the expired session
            clearMatches();
          }
          setClientJobs([]);
          setClientTotal(0);
        } else {
          // Convert MatchResult[] to Job[]
          const jobsFromMatches: Job[] = data.matches.map((match) => ({
            id: match.job_id,
            source: "",
            title: match.title,
            company: match.company,
            location: match.location,
            city: null,
            state: null,
            country: null,
            apply_url: "",
            description_text: "",
            job_category: null,
            job_type: null,
            work_mode: null,
            posted_at: null,
            is_active: true,
          }));
          setClientJobs(jobsFromMatches);
          setClientTotal(data.total);
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadMatchedJobs();
  }, [
    matched,
    isMatchStateLoading,
    sessionId,
    currentPage,
    searchQuery,
    company,
    location,
    category,
    jobType,
    workMode,
    postedWithin,
    clearMatches,
  ]);

  useEffect(() => {
    if (matched) return;
    setAppendedJobs([]);
    setLastLoadedPage(currentPage);
  }, [
    matched,
    currentPage,
    searchQuery,
    company,
    location,
    category,
    jobType,
    workMode,
    postedWithin,
    serverJobs,
  ]);

  const handleLoadMore = useCallback(async () => {
    if (matched || isLoadingMore) return;

    const nextPage = lastLoadedPage + 1;
    if (nextPage > totalPagesComputed) return;

    setIsLoadingMore(true);
    try {
      const data = await fetchJobs({
        page: nextPage,
        page_size: DEFAULT_PAGE_SIZE,
        search: searchQuery,
        company,
        location,
        category,
        job_type: jobType,
        work_mode: workMode,
        posted_within: postedWithin,
      });

      setAppendedJobs((prev) => {
        const existingIds = new Set([...(serverJobs || []).map((job) => job.id), ...prev.map((job) => job.id)]);
        const fresh = data.items.filter((job) => !existingIds.has(job.id));
        return [...prev, ...fresh];
      });
      setLastLoadedPage(nextPage);
    } finally {
      setIsLoadingMore(false);
    }
  }, [
    matched,
    isLoadingMore,
    lastLoadedPage,
    totalPagesComputed,
    searchQuery,
    company,
    location,
    category,
    jobType,
    workMode,
    postedWithin,
    serverJobs,
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

  const handleRequireAuthForApply = useCallback((applyUrl: string) => {
    setPendingApplyUrl(applyUrl);
    sessionStorage.setItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL, applyUrl);
    setIsAuthModalOpen(true);
  }, []);

  const openApplyUrl = useCallback((url: string, targetWindow?: Window | null) => {
    if (targetWindow && !targetWindow.closed) {
      targetWindow.location.href = url;
      return;
    }

    const openedWindow = window.open(url, "_blank", "noopener,noreferrer");
    if (!openedWindow) {
      setShowPopupBlockedToast(true);
    }
  }, []);

  const handleApplyAfterAuth = useCallback((applyWindow?: Window | null) => {
    const urlToOpen = pendingApplyUrl || sessionStorage.getItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
    if (!urlToOpen) {
      setIsAuthModalOpen(false);
      return;
    }

    openApplyUrl(urlToOpen, applyWindow);

    sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
    setPendingApplyUrl(null);
    setIsAuthModalOpen(false);
  }, [openApplyUrl, pendingApplyUrl]);

  useEffect(() => {
    if (!isAuthenticated) return;

    const storedApplyUrl = sessionStorage.getItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
    if (!storedApplyUrl) return;

    openApplyUrl(storedApplyUrl);
    sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
    setPendingApplyUrl(null);
    setIsAuthModalOpen(false);
  }, [isAuthenticated, openApplyUrl]);

  useEffect(() => {
    if (!showPopupBlockedToast) return;
    const timeoutId = window.setTimeout(() => setShowPopupBlockedToast(false), 5000);
    return () => window.clearTimeout(timeoutId);
  }, [showPopupBlockedToast]);

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
        {SHOW_JOB_COUNT && (
          <span className="text-sm text-slate-500 dark:text-md-on-surface-variant">
            {total} {matched ? "matches" : "openings"}
          </span>
        )}
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

          {!matched && jobs.length > 0 && jobs.length < total && (
            <div className="mt-6 flex flex-col items-center gap-3 sm:hidden">
              <button
                type="button"
                onClick={handleLoadMore}
                disabled={isLoadingMore}
                className="rounded-lg border border-slate-300 bg-white px-5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
              >
                {isLoadingMore ? "Loading..." : `Load ${DEFAULT_PAGE_SIZE} more`}
              </button>
              <span className="text-xs text-slate-500 dark:text-md-on-surface-variant">
                Showing {jobs.length} of {total}
              </span>
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
            <div className="hidden sm:block">
              <Pagination
                currentPage={currentPage}
                totalPages={totalPagesComputed}
                buildPageUrl={buildPageUrl}
              />
            </div>
          ) : null}
        </div>

        {selectedSlug && (
          <JobDetailPanelContainer
            job={selectedJob}
            onClose={handleClose}
            isAuthenticated={isAuthenticated}
            onRequireAuthForApply={handleRequireAuthForApply}
          />
        )}
      </div>
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => {
          setIsAuthModalOpen(false);
          setPendingApplyUrl(null);
          sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
        }}
        defaultMode="login"
        onAuthSuccess={handleApplyAfterAuth}
        intent="apply"
      />
      {showPopupBlockedToast && (
        <Toast
          type="warning"
          message="Popup blocked. Please allow popups for this site, then try Apply again."
          onClose={() => setShowPopupBlockedToast(false)}
        />
      )}
    </section>
  );
}
