'use client';

import Link from 'next/link';
import dynamic from 'next/dynamic';
import { markApplied, saveJob, unsaveJob } from '@/app/actions/user';
import Pagination from '@/components/ui/Pagination';
import { Alert, Button, Toast } from '@/components/ui';
import { DEFAULT_PAGE_SIZE, SESSION_STORAGE_KEYS } from '@/lib/constants';
import { JobDetailPanelContainer } from './JobDetailPanelContainer';
import { JobCard } from './JobCard';
import { useJobList } from './useJobList';
import { SHOW_JOB_COUNT } from '@/lib/config';
import type { JobSummary } from '@/lib/types/job';

const AuthModal = dynamic(() => import('@/components/auth/AuthModal'), { ssr: false });

interface JobListProps {
  readonly jobs?: JobSummary[];
  readonly total?: number;
  readonly totalPages?: number;
  readonly currentPage: number;
  readonly matched?: boolean;
  readonly isAuthenticated?: boolean;
  readonly initialSavedJobIds?: string[];
  readonly initialAppliedJobIds?: string[];
}

function JobListHeading({
  matched,
  total,
}: {
  readonly matched: boolean;
  readonly total?: number;
}) {
  const singularLabel = matched ? 'match' : 'opening';
  const resultLabel = total === 1 ? singularLabel : `${singularLabel}s`;
  return (
    <div className="flex items-center justify-between">
      <h2 className="text-foreground text-xl font-semibold">
        {matched ? 'Matched roles' : 'Latest roles'}
      </h2>
      {SHOW_JOB_COUNT && total !== undefined && (
        <span className="text-foreground-muted text-sm">
          {total.toLocaleString('en-US')} {resultLabel}
        </span>
      )}
    </div>
  );
}

function LoadingJobList({ matched }: { readonly matched: boolean }) {
  return (
    <section className="space-y-4">
      <JobListHeading matched={matched} />
      <div className="space-y-3" aria-busy="true" aria-label="Loading matched jobs">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="border-border bg-surface animate-pulse rounded-xl border p-5">
            <div className="bg-border h-5 w-2/3 rounded" />
            <div className="bg-surface-subtle mt-3 h-4 w-1/3 rounded" />
            <div className="bg-surface-subtle mt-4 h-6 w-28 rounded-full" />
          </div>
        ))}
      </div>
    </section>
  );
}

function JobListPagination({
  matched,
  currentPage,
  totalPages,
  buildPageUrl,
}: {
  readonly matched: boolean;
  readonly currentPage: number;
  readonly totalPages: number;
  readonly buildPageUrl: (page: number) => string;
}) {
  const linkClassName =
    'border-border bg-surface text-foreground-secondary hover:bg-surface-subtle focus-visible:ring-focus-ring rounded-lg border px-4 py-2 text-sm font-medium focus-visible:ring-2 focus-visible:outline-none';
  if (totalPages <= 1) return null;
  if (!matched) {
    return (
      <div className="hidden sm:block">
        <Pagination currentPage={currentPage} totalPages={totalPages} buildPageUrl={buildPageUrl} />
      </div>
    );
  }
  return (
    <div className="mt-8 flex items-center justify-center gap-2">
      {currentPage > 1 && (
        <Link href={buildPageUrl(currentPage - 1)} className={linkClassName}>
          Previous
        </Link>
      )}
      <span className="text-foreground-secondary px-4 py-2 text-sm">
        Page {currentPage} of {totalPages}
      </span>
      {currentPage < totalPages && (
        <Link href={buildPageUrl(currentPage + 1)} className={linkClassName}>
          Next
        </Link>
      )}
    </div>
  );
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
    listError,
    selectedJob,
    selectedJobDetail,
    isJobDetailLoading,
    jobDetailError,
    isJobUnavailable,
    retryJobDetail,
    selectedSlug,
    matchScoresMap,
    savedJobIds,
    appliedJobIds,
    pendingSaveJobIds,
    pendingAppliedJobIds,
    isAuthModalOpen,
    saveAuthModalOpen,
    actionToast,
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
    setActionToast,
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
    return <LoadingJobList matched={matched} />;
  }

  return (
    <section className="space-y-4">
      <JobListHeading matched={matched} total={total} />

      <div className="flex flex-col gap-6 lg:flex-row">
        <div
          className={`transition-all duration-300 ${selectedJob ? 'w-full lg:w-1/2' : 'w-full'}`}
        >
          {listError && (
            <Alert type="error" className="mb-4">
              <div>
                <p>{listError}</p>
                {!matched && (
                  <button
                    type="button"
                    onClick={handleLoadMore}
                    className="mt-2 text-sm font-medium underline underline-offset-4"
                  >
                    Try again
                  </button>
                )}
              </div>
            </Alert>
          )}

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
                isSavePending={pendingSaveJobIds.has(job.id)}
                onToggleSave={(shouldSave) => handleToggleSave(job.id, shouldSave)}
                isApplied={appliedJobIds.has(job.id)}
                isAppliedPending={pendingAppliedJobIds.has(job.id)}
                onToggleApplied={(shouldApply) => handleToggleApplied(job.id, shouldApply)}
              />
            );
          })}

          {jobs.length === 0 && !listError && (
            <div className="border-border bg-surface rounded-2xl border p-8 text-center">
              <p className="text-foreground-muted">
                {matched ? 'No matched jobs found.' : 'No jobs found.'}
              </p>
            </div>
          )}

          {!matched && jobs.length > 0 && jobs.length < total && (
            <div className="mt-6 flex flex-col items-center gap-3 sm:hidden">
              <Button onClick={handleLoadMore} disabled={isLoadingMore} variant="secondary">
                {isLoadingMore ? 'Loading...' : `Load ${DEFAULT_PAGE_SIZE} more`}
              </Button>
            </div>
          )}

          <JobListPagination
            matched={matched}
            currentPage={currentPage}
            totalPages={totalPagesComputed}
            buildPageUrl={buildPageUrl}
          />
        </div>

        {selectedSlug && (
          <JobDetailPanelContainer
            job={selectedJob}
            detail={selectedJobDetail}
            isLoading={isJobDetailLoading}
            error={jobDetailError}
            isUnavailable={isJobUnavailable}
            onRetry={retryJobDetail}
            onClose={handleClose}
            isAuthenticated={isAuthenticated}
            onRequireAuthForApply={handleRequireAuthForApply}
            isApplied={selectedJob ? appliedJobIds.has(selectedJob.id) : false}
            isAppliedPending={selectedJob ? pendingAppliedJobIds.has(selectedJob.id) : false}
            onToggleApplied={(shouldApply) => {
              if (!selectedJob) return;
              handleToggleApplied(selectedJob.id, shouldApply);
            }}
            onApply={handleApply}
          />
        )}
      </div>

      {isAuthModalOpen && (
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
      )}

      {actionToast && (
        <Toast
          type={actionToast.type}
          message={actionToast.message}
          onClose={() => setActionToast(null)}
        />
      )}

      {pendingAppliedConfirmJobId && (
        <div className="border-border bg-surface fixed right-4 bottom-4 z-[70] w-[calc(100%-2rem)] max-w-sm rounded-xl border p-4 shadow-lg">
          <p className="text-foreground text-sm font-medium">Did you apply to this job?</p>
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
                  setActionToast({ type: 'success', message: 'Job marked as applied.' });
                } else {
                  setActionToast({
                    type: 'error',
                    message: result.error || 'Unable to update this application. Please try again.',
                  });
                }
                setPendingAppliedConfirmJobId(null);
              }}
            >
              Yes
            </button>
            <Button variant="secondary" onClick={() => setPendingAppliedConfirmJobId(null)}>
              No
            </Button>
          </div>
        </div>
      )}

      {saveAuthModalOpen && (
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
                setActionToast({
                  type: 'success',
                  message: shouldSave ? 'Job saved.' : 'Job removed from saved jobs.',
                });
              } else {
                setActionToast({
                  type: 'error',
                  message: result.error || 'Unable to update this saved job. Please try again.',
                });
              }
            }
            setSaveAuthModalOpen(false);
            setPendingSaveJobId(null);
            setPendingSaveState(null);
          }}
        />
      )}
    </section>
  );
}
