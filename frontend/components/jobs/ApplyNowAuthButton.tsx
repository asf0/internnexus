"use client";

import { useCallback, useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { AuthModal } from "@/components/auth";
import { Toast } from "@/components/ui";
import { SESSION_STORAGE_KEYS } from "@/lib/constants";

interface ApplyNowAuthButtonProps {
  applyUrl: string;
  isAuthenticated: boolean;
}

export default function ApplyNowAuthButton({ applyUrl, isAuthenticated }: ApplyNowAuthButtonProps) {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [pendingApplyUrl, setPendingApplyUrl] = useState<string | null>(null);
  const [showPopupBlockedToast, setShowPopupBlockedToast] = useState(false);

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

  const handleClick = useCallback(() => {
    if (isAuthenticated) {
      openApplyUrl(applyUrl);
      return;
    }

    setPendingApplyUrl(applyUrl);
    sessionStorage.setItem(SESSION_STORAGE_KEYS.PENDING_APPLY_URL, applyUrl);
    setIsAuthModalOpen(true);
  }, [applyUrl, isAuthenticated, openApplyUrl]);

  const handleAuthSuccess = useCallback((applyWindow?: Window | null) => {
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

  return (
    <>
      {isAuthenticated ? (
        <a
          href={applyUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700"
        >
          Apply Now
          <ExternalLink className="h-4 w-4" />
        </a>
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
        }}
        defaultMode="login"
        onAuthSuccess={handleAuthSuccess}
        intent="apply"
      />

      {showPopupBlockedToast && (
        <Toast
          type="warning"
          message="Popup blocked. Please allow popups for this site, then try Apply again."
          onClose={() => setShowPopupBlockedToast(false)}
        />
      )}
    </>
  );
}
