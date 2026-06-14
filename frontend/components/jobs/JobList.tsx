'use client';

import Link from 'next/link';
import { markApplied, saveJob, unsaveJob } from '@/app/actions/user';
import Pagination from '@/components/ui/Pagination';
import { LoadingSpinner, Toast } from '@/components/ui';
import { AuthModal } from '@/components/auth';
import { SESSION_STORAGE_KEYS } from '@/lib/constants';
import { JobDetailPanelContainer } from './JobDetailPanelContainer';
import { JobCard } from './JobCard';
import { useJobList } from './useJobList';
import { SHOW_JOB_COUNT } from '@/lib/config';
import { DEFAULT_PAGE_SIZE } from '@/lib/constants';
import type { Job } from '@/lib/types/job';

interface JobListProps {
  readonly jobs?: Job[];
  readonly total?: number;
  readonly totalPages?: number;
  readonly currentPage: number;
  readonly matched?: boolean;
  readonly isAuthenticated?: boolean;
  readonly initialSavedJobIds?: string[];
  readonly initialAppliedJobIds?: string[];
}

export default function JobList({
  jobs: serverJobs,
  total: serverTotal,
  totalPages: serverTotalPages,
  currentPage,
  matched = false,
  isAuthenticated = false,
  initialSavedJobIds = [],
  initialAppliedJobIds = [],
}: JobListProps) {
  const {
    jobs,
    total,
    totalPagesComputed,
    isLoading,
    isLoadingMore,
    selectedJob,
    selectedSlug,
    matchScoresMap,
    savedJobIds,
    appliedJobIds,
    isAuthModalOpen,
    saveAuthModalOpen,
    applyToastMessage,
    pendingAppliedConfirmJobId,
    pendingSaveJobId,
    pendingSaveState,
    setIsAuthModalOpen,
    setSaveAuthModalOpen,
    setPendingSaveJobId,
    setPendingSaveState,
    setPendingApplyUrl,
    setPendingApplyJobId,
    setSavedJobIds,
    setAppliedJobIds,
    setPendingAppliedConfirmJobId,
    setApplyToastMessage,
    handleLoadMore,
    handleJobClick,
    handleClose,
    handleToggleSave,
    handleToggleApplied,
    handleRequireAuthForApply,
    handleApplyAfterAuth,
    handleApply,
    buildPageUrl,
  } = useJobList({
    jobs: serverJobs,
    total: serverTotal,
    totalPages: serverTotalPages,
    currentPage,
    matched,
    isAuthenticated,
    initialSavedJobIds,
    initialAppliedJobIds,
  });

  if (isLoading) {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="dark:text-md-on-surface text-xl font-semibold">
            {matched ? 'Matched roles' : 'Latest roles'}
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
        <h2 className="dark:text-md-on-surface text-xl font-semibold">
          {matched ? 'Matched roles' : 'Latest roles'}
        </h2>
        {SHOW_JOB_COUNT && (
          <span className="dark:text-md-on-surface-variant text-sm text-slate-500">
            {total} {matched ? 'matches' : 'openings'}
          </span>
        )}
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        <div
          className={`transition-all duration-300 ${selectedJob ? 'w-full lg:w-1/2' : 'w-full'}`}
        >
          {jobs.map((job) => {
            const matchPercentage = matched ? matchScoresMap.get(job.id) : undefined;
            return (
              <JobCard
                key={job.id}
                job={job}
                isSelected={selectedJob?.id === job.id}
                matchPercentage={matchPercentage}
                onClick={() => handleJobClick(job)}
                isSaved={savedJobIds.has(job.id)}
                onToggleSave={(shouldSave) => handleToggleSave(job.id, shouldSave)}
                isApplied={appliedJobIds.has(job.id)}
                onToggleApplied={(shouldApply) => handleToggleApplied(job.id, shouldApply)}
              />
            );
          })}

          {jobs.length === 0 && (
            <div className="dark:border-md-outline-variant dark:bg-md-surface-container-low rounded-2xl border border-slate-200 bg-white p-8 text-center">
              <p className="dark:text-md-on-surface-variant text-slate-500">
                {matched ? 'No matched jobs found.' : 'No jobs found.'}
              </p>
            </div>
          )}

          {!matched && jobs.length > 0 && jobs.length < total && (
            <div className="mt-6 flex flex-col items-center gap-3 sm:hidden">
              <button
                type="button"
                onClick={handleLoadMore}
                disabled={isLoadingMore}
                className="dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high rounded-lg border border-slate-300 bg-white px-5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isLoadingMore ? 'Loading...' : `Load ${DEFAULT_PAGE_SIZE} more`}
              </button>
              <span className="dark:text-md-on-surface-variant text-xs text-slate-500">
                Showing {jobs.length} of {total}
              </span>
            </div>
          )}

          {matched && totalPagesComputed > 1 ? (
            <div className="mt-8 flex items-center justify-center gap-2">
              {currentPage > 1 && (
                <Link
                  href={buildPageUrl(currentPage - 1)}
                  className="dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Previous
                </Link>
              )}

              <span className="dark:text-md-on-surface-variant px-4 py-2 text-sm text-slate-600">
                Page {currentPage} of {totalPagesComputed}
              </span>

              {currentPage < totalPagesComputed && (
                <Link
                  href={buildPageUrl(currentPage + 1)}
                  className="dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
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
            isApplied={selectedJob ? appliedJobIds.has(selectedJob.id) : false}
            onToggleApplied={(shouldApply) => {
              if (!selectedJob) return;
              handleToggleApplied(selectedJob.id, shouldApply);
            }}
            onApply={handleApply}
          />
        )}
      </div>

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => {
          setIsAuthModalOpen(false);
          setPendingApplyUrl(null);
          setPendingApplyJobId(null);
          sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
          sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_JOB_ID);
        }}
        defaultMode="login"
        onAuthSuccess={handleApplyAfterAuth}
        intent="apply"
      />

      {applyToastMessage && (
        <Toast
          type="warning"
          message={applyToastMessage}
          onClose={() => setApplyToastMessage(null)}
        />
      )}

      {pendingAppliedConfirmJobId && (
        <div className="dark:border-md-outline-variant dark:bg-md-surface-container fixed right-4 bottom-4 z-[70] w-full max-w-sm rounded-xl border border-slate-200 bg-white p-4 shadow-lg">
          <p className="dark:text-md-on-surface text-sm font-medium text-slate-900">
            Did you apply to this job?
          </p>
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700"
              onClick={async () => {
                const jobId = pendingAppliedConfirmJobId;
                if (!jobId) {
                  setPendingAppliedConfirmJobId(null);
                  return;
                }
                const result = await markApplied(jobId);
                if (result.success) {
                  setAppliedJobIds((prev) => {
                    const next = new Set(prev);
                    next.add(jobId);
                    return next;
                  });
                }
                setPendingAppliedConfirmJobId(null);
              }}
            >
              Yes
            </button>
            <button
              type="button"
              className="dark:border-md-outline-variant dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
              onClick={() => setPendingAppliedConfirmJobId(null)}
            >
              No
            </button>
          </div>
        </div>
      )}

      <AuthModal
        isOpen={saveAuthModalOpen}
        onClose={() => {
          setSaveAuthModalOpen(false);
          setPendingSaveJobId(null);
          setPendingSaveState(null);
        }}
        defaultMode="login"
        onAuthSuccess={async () => {
          const jobId = pendingSaveJobId;
          const shouldSave = pendingSaveState;
          if (jobId && shouldSave !== null) {
            const result = shouldSave ? await saveJob(jobId) : await unsaveJob(jobId);
            if (result.success) {
              setSavedJobIds((prev) => {
                const next = new Set(prev);
                if (shouldSave) next.add(jobId);
                else next.delete(jobId);
                return next;
              });
            }
          }
          setSaveAuthModalOpen(false);
          setPendingSaveJobId(null);
          setPendingSaveState(null);
        }}
      />
    </section>
  );
}
