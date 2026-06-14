'use client';

import { useMatchState } from '@/lib/hooks/useMatchState';
import { useJobListData } from './useJobListData';
import { useJobSelection } from './useJobSelection';
import { useJobActions } from './useJobActions';
import type { Job } from '@/lib/types/job';

interface UseJobListProps {
  readonly jobs: Job[] | undefined;
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
    isAuthModalOpen,
    saveAuthModalOpen,
    applyToastMessage,
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
    setApplyToastMessage,
    setPendingAppliedConfirmJobId,
    handleToggleSave,
    handleToggleApplied,
    handleRequireAuthForApply,
    handleApplyAfterAuth,
    handleApply,
  } = useJobActions({ isAuthenticated, initialSavedJobIds, initialAppliedJobIds });

  const { jobs, total, totalPagesComputed, isLoading, isLoadingMore, handleLoadMore } =
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

  return {
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
  };
}
