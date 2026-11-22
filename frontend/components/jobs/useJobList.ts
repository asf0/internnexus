'use client';

import { useMatchState } from '@/lib/hooks/useMatchState';
import { useJobListData } from './useJobListData';
import { useJobSelection } from './useJobSelection';
import { useJobDetail } from './useJobDetail';
import { useJobActions } from './useJobActions';
import type { JobSummary } from '@/lib/types/job';

interface UseJobListProps {
  readonly jobs: JobSummary[] | undefined;
  readonly total: number | undefined;
  readonly totalPages: number | undefined;
  readonly currentPage: number;
  readonly matched: boolean;
  readonly isAuthenticated: boolean;
  readonly initialSavedJobIds: string[];
  readonly initialAppliedJobIds: string[];
}

export function useJobList({
  jobs: serverJobs,
  total: serverTotal,
  totalPages: serverTotalPages,
  currentPage,
  matched,
  isAuthenticated,
  initialSavedJobIds,
  initialAppliedJobIds,
}: UseJobListProps) {
  const {
    sessionId,
    matchScores: matchScoresMap,
    clearMatches,
    isLoading: isMatchStateLoading,
  } = useMatchState();

  const {
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
    pendingApplyUrl,
    pendingApplyJobId,
    setSavedJobIds,
    setAppliedJobIds,
    setIsAuthModalOpen,
    setSaveAuthModalOpen,
    setPendingSaveJobId,
    setPendingSaveState,
    setPendingApplyUrl,
    setPendingApplyJobId,
    setActionToast,
    setPendingAppliedConfirmJobId,
    handleToggleSave,
    handleToggleApplied,
    handleRequireAuthForApply,
    handleApplyAfterAuth,
    handleApply,
  } = useJobActions({ isAuthenticated, initialSavedJobIds, initialAppliedJobIds });

  const { jobs, total, totalPagesComputed, isLoading, isLoadingMore, listError, handleLoadMore } =
    useJobListData({
      serverJobs,
      serverTotal,
      serverTotalPages,
      currentPage,
      matched,
      savedJobIds,
      sessionId,
      isMatchStateLoading,
      clearMatches,
    });

  const { selectedSlug, selectedJob, handleJobClick, handleClose, buildPageUrl } =
    useJobSelection(jobs);
  const {
    detail: selectedJobDetail,
    isLoading: isJobDetailLoading,
    error: jobDetailError,
    isUnavailable: isJobUnavailable,
    retry: retryJobDetail,
  } = useJobDetail(selectedJob?.id ?? null);

  return {
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
    pendingApplyUrl,
    pendingApplyJobId,
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
  };
}
