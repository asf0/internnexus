'use client';

import { useCallback, useEffect, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { AuthModal } from '@/components/auth';
import { Toast } from '@/components/ui';
import { SESSION_STORAGE_KEYS } from '@/lib/constants';
import { toSafeHttpUrl } from '@/lib/utils';
import { trackJobClick } from '@/app/actions/jobs';

interface ApplyNowAuthButtonProps {
  readonly jobId: string;
  readonly applyUrl: string;
  readonly isAuthenticated: boolean;
}

export default function ApplyNowAuthButton({
  jobId,
  applyUrl,
  isAuthenticated,
}: ApplyNowAuthButtonProps) {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [pendingApplyUrl, setPendingApplyUrl] = useState<string | null>(null);
  const [applyToastMessage, setApplyToastMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

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

  const handleAuthenticatedClick = useCallback(async () => {
    if (isLoading) return;

    setIsLoading(true);
    try {
      const result = await trackJobClick(jobId);

      if ('error' in result) {
        // Fallback to original URL on error
        openApplyUrl(applyUrl);
        return;
      }

      openApplyUrl(result.apply_url);
    } finally {
      setIsLoading(false);
    }
  }, [jobId, applyUrl, isLoading, openApplyUrl]);

  const handleClick = useCallback(() => {
    if (isAuthenticated) {
      handleAuthenticatedClick();
      return;
    }

    const safeApplyUrl = toSafeHttpUrl(applyUrl);
    if (!safeApplyUrl) {
      setApplyToastMessage('This apply link is invalid or unsupported.');
      return;
    }

    setPendingApplyUrl(safeApplyUrl);
    sessionStorage.setItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL, safeApplyUrl);
    sessionStorage.setItem(SESSION_STORAGE_KEYS.PENDING_APPLY_JOB_ID, jobId);
    setIsAuthModalOpen(true);
  }, [applyUrl, jobId, isAuthenticated, handleAuthenticatedClick]);

  const handleAuthSuccess = useCallback(
    async (applyWindow?: Window | null) => {
      const urlToOpen =
        pendingApplyUrl || sessionStorage.getItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
      const storedJobId = sessionStorage.getItem(SESSION_STORAGE_KEYS.PENDING_APPLY_JOB_ID);

      if (!urlToOpen) {
        setIsAuthModalOpen(false);
        return;
      }

      // Track the click after auth
      if (storedJobId) {
        try {
          const result = await trackJobClick(storedJobId);
          if (!('error' in result)) {
            openApplyUrl(result.apply_url, applyWindow);
            sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
            sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_JOB_ID);
            setPendingApplyUrl(null);
            setIsAuthModalOpen(false);
            return;
          }
        } catch {
          // Fall through to use original URL
        }
      }

      openApplyUrl(urlToOpen, applyWindow);
      sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
      sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_JOB_ID);
      setPendingApplyUrl(null);
      setIsAuthModalOpen(false);
    },
    [openApplyUrl, pendingApplyUrl]
  );

  useEffect(() => {
    if (!isAuthenticated) return;

    const storedApplyUrl = sessionStorage.getItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
    const storedJobId = sessionStorage.getItem(SESSION_STORAGE_KEYS.PENDING_APPLY_JOB_ID);
    if (!storedApplyUrl) return;

    // Track click and open URL after auth
    const openAfterAuth = async () => {
      if (storedJobId) {
        try {
          const result = await trackJobClick(storedJobId);
          if (!('error' in result)) {
            openApplyUrl(result.apply_url);
            sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
            sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_JOB_ID);
            setPendingApplyUrl(null);
            setIsAuthModalOpen(false);
            return;
          }
        } catch {
          // Fall through to use original URL
        }
      }

      openApplyUrl(storedApplyUrl);
      sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
      sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_JOB_ID);
      setPendingApplyUrl(null);
      setIsAuthModalOpen(false);
    };

    openAfterAuth();
  }, [isAuthenticated, openApplyUrl]);

  useEffect(() => {
    if (!applyToastMessage) return;
    const timeoutId = window.setTimeout(() => setApplyToastMessage(null), 5000);
    return () => window.clearTimeout(timeoutId);
  }, [applyToastMessage]);

  return (
    <>
      {isAuthenticated ? (
        <button
          type="button"
          onClick={handleAuthenticatedClick}
          disabled={isLoading}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? 'Loading...' : 'Apply Now'}
          <ExternalLink className="h-4 w-4" />
        </button>
      ) : (
        <button
          type="button"
          onClick={handleClick}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700"
        >
          Apply Now
          <ExternalLink className="h-4 w-4" />
        </button>
      )}

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => {
          setIsAuthModalOpen(false);
          setPendingApplyUrl(null);
          sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL);
          sessionStorage.removeItem(SESSION_STORAGE_KEYS.PENDING_APPLY_JOB_ID);
        }}
        defaultMode="login"
        onAuthSuccess={handleAuthSuccess}
        intent="apply"
      />

      {applyToastMessage && (
        <Toast
          type="warning"
          message={applyToastMessage}
          onClose={() => setApplyToastMessage(null)}
        />
      )}
    </>
  );
}
