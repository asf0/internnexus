'use client';

import { useState, useEffect, useCallback } from 'react';
import { markApplied, saveJob, unmarkApplied, unsaveJob } from '@/app/actions/user';
import { trackJobClick } from '@/app/actions/jobs';
import { SESSION_STORAGE_KEYS } from '@/lib/constants';
import { toSafeHttpUrl } from '@/lib/utils';

interface UseJobActionsProps {
  readonly isAuthenticated: boolean;
  readonly initialSavedJobIds: string[];
  readonly initialAppliedJobIds: string[];
}

export function useJobActions({
  isAuthenticated,
  initialSavedJobIds,
  initialAppliedJobIds,
}: UseJobActionsProps) {
  const [savedJobIds, setSavedJobIds] = useState<Set<string>>(new Set(initialSavedJobIds));
  const [appliedJobIds, setAppliedJobIds] = useState<Set<string>>(new Set(initialAppliedJobIds));

  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [pendingApplyUrl, setPendingApplyUrl] = useState<string | null>(null);
  const [pendingApplyJobId, setPendingApplyJobId] = useState<string | null>(null);
  const [applyToastMessage, setApplyToastMessage] = useState<string | null>(null);

  const [saveAuthModalOpen, setSaveAuthModalOpen] = useState(false);
  const [pendingSaveJobId, setPendingSaveJobId] = useState<string | null>(null);
  const [pendingSaveState, setPendingSaveState] = useState<boolean | null>(null);

  const [pendingAppliedConfirmJobId, setPendingAppliedConfirmJobId] = useState<string | null>(null);

  const handleToggleSave = useCallback(
    async (jobId: string, shouldSave: boolean) => {
      if (!isAuthenticated) {
        setPendingSaveJobId(jobId);
        setPendingSaveState(shouldSave);
        setSaveAuthModalOpen(true);
        return;
      }

      const result = shouldSave ? await saveJob(jobId) : await unsaveJob(jobId);
      if (!result.success) return;

      setSavedJobIds((prev) => {
        const next = new Set(prev);
        if (shouldSave) next.add(jobId);
        else next.delete(jobId);
        return next;
      });
    },
    [isAuthenticated]
  );

  const handleToggleApplied = useCallback(
    async (jobId: string, shouldApply: boolean) => {
      if (!isAuthenticated) return;
      const result = shouldApply ? await markApplied(jobId) : await unmarkApplied(jobId);
      if (!result.success) return;
      setAppliedJobIds((prev) => {
        const next = new Set(prev);
        if (shouldApply) next.add(jobId);
        else next.delete(jobId);
        return next;
      });
    },
    [isAuthenticated]
  );

  const promptAppliedConfirmation = useCallback((jobId: string) => {
    setPendingAppliedConfirmJobId(jobId);
  }, []);

  const openApplyUrl = useCallback((url: string, targetWindow?: Window | null) => {
    const safeUrl = toSafeHttpUrl(url);
    if (!safeUrl) {
      setApplyToastMessage('This apply link is invalid or unsupported.');
      return false;
    }

    if (targetWindow && !targetWindow.closed) {
      targetWindow.location.href = safeUrl;
      return true;
    }

    const openedWindow = window.open(safeUrl, '_blank', 'noopener,noreferrer');
    if (!openedWindow) {
      setApplyToastMessage(
        'Popup blocked. Please allow popups for this site, then try Apply again.'
      );
      return false;
    }
    return true;
  }, []);

  const handleRequireAuthForApply = useCallback((applyUrl: string, jobId: string) => {
    const safeApplyUrl = toSafeHttpUrl(applyUrl);
    if (!safeApplyUrl) {
      setApplyToastMessage('This apply link is invalid or unsupported.');
      return;
    }

    setPendingApplyUrl(safeApplyUrl);
    setPendingApplyJobId(jobId);
    sessionStorage.setItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL, safeApplyUrl);
    sessionStorage.setItem(SESSION_STORAGE_KEYS.PENDING_APPLY_JOB_ID, jobId);
    setIsAuthModalOpen(true);
  }, []);

  const clearPendingApply = useCallback(() => {
    sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
    sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_JOB_ID);
    setPendingApplyUrl(null);
    setPendingApplyJobId(null);
  }, []);

  const handleApplyAfterAuth = useCallback(
    async (applyWindow?: Window | null) => {
      const urlToOpen =
        pendingApplyUrl || sessionStorage.getItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
      const jobIdToTrack =
        pendingApplyJobId || sessionStorage.getItem(SESSION_STORAGE_KEYS.PENDING_APPLY_JOB_ID);

      if (!urlToOpen) {
        setIsAuthModalOpen(false);
        return;
      }

      if (jobIdToTrack) {
        try {
          const result = await trackJobClick(jobIdToTrack);
          if (!('error' in result)) {
            openApplyUrl(result.apply_url, applyWindow);
            promptAppliedConfirmation(jobIdToTrack);
            clearPendingApply();
            setIsAuthModalOpen(false);
            return;
          }
        } catch {
          // Fall through to use original URL
        }
      }

      openApplyUrl(urlToOpen, applyWindow);
      clearPendingApply();
      setIsAuthModalOpen(false);
    },
    [openApplyUrl, pendingApplyUrl, pendingApplyJobId, promptAppliedConfirmation, clearPendingApply]
  );

  useEffect(() => {
    if (!isAuthenticated) return;

    const storedApplyUrl = sessionStorage.getItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
    const storedJobId = sessionStorage.getItem(SESSION_STORAGE_KEYS.PENDING_APPLY_JOB_ID);
    if (!storedApplyUrl) return;

    const openAfterAuth = async () => {
      if (storedJobId) {
        try {
          const result = await trackJobClick(storedJobId);
          if (!('error' in result)) {
            openApplyUrl(result.apply_url);
            promptAppliedConfirmation(storedJobId);
            clearPendingApply();
            setIsAuthModalOpen(false);
            return;
          }
        } catch {
          // Fall through to use original URL
        }
      }

      openApplyUrl(storedApplyUrl);
      clearPendingApply();
      setIsAuthModalOpen(false);
    };

    openAfterAuth();
  }, [isAuthenticated, openApplyUrl, promptAppliedConfirmation, clearPendingApply]);

  const handleApply = useCallback(
    async (jobId: string, applyUrl: string) => {
      if (!isAuthenticated) {
        handleRequireAuthForApply(applyUrl, jobId);
        return;
      }
      try {
        const result = await trackJobClick(jobId);
        if (!('error' in result)) {
          openApplyUrl(result.apply_url);
          promptAppliedConfirmation(jobId);
          return;
        }
      } catch {
        // fallback below
      }
      openApplyUrl(applyUrl);
      promptAppliedConfirmation(jobId);
    },
    [isAuthenticated, handleRequireAuthForApply, openApplyUrl, promptAppliedConfirmation]
  );

  useEffect(() => {
    if (!applyToastMessage) return;
    const timeoutId = window.setTimeout(() => setApplyToastMessage(null), 5000);
    return () => window.clearTimeout(timeoutId);
  }, [applyToastMessage]);

  return {
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
  };
}
