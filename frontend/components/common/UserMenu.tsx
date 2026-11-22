'use client';

import { logoutUser } from '@/app/actions/auth';
import { User, LogOut, ChevronDown, Settings, UserCircle, Sparkles, Bell } from 'lucide-react';
import { useEffect, useId, useRef, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { isSafeInternalPath } from '@/lib/navigation';

const AuthModal = dynamic(() => import('@/components/auth/AuthModal'), { ssr: false });

interface UserMenuProps {
  readonly user?: {
    readonly name?: string | null;
    readonly email?: string | null;
    readonly image?: string | null;
  } | null;
  readonly autoOpenAuthModal?: boolean;
  readonly postAuthRedirectPath?: string;
  readonly unreadCount?: number;
}

export default function UserMenu({
  user,
  autoOpenAuthModal = false,
  postAuthRedirectPath,
  unreadCount = 0,
}: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState<'login' | 'register'>('login');
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const hasAutoOpened = useRef(false);
  const menuId = useId();
  const router = useRouter();

  useEffect(() => {
    if (!user && autoOpenAuthModal && !hasAutoOpened.current) {
      hasAutoOpened.current = true;
      setAuthModalMode('login');
      setIsAuthModalOpen(true);
    }
  }, [user, autoOpenAuthModal]);

  useEffect(() => {
    if (!isOpen) return;

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [isOpen]);
  const handleLogout = async () => {
    setLogoutError(null);
    const result = await logoutUser();
    if (!result.success) {
      setLogoutError(result.error);
      return;
    }

    setIsOpen(false);
    router.push('/');
    router.refresh();
  };

  if (!user) {
    return (
      <>
        <button
          type="button"
          onClick={() => {
            setAuthModalMode('login');
            setIsAuthModalOpen(true);
          }}
          className="bg-accent text-on-accent hover:bg-accent-hover focus-visible:ring-focus-ring rounded-lg px-3 py-2 text-sm font-medium whitespace-nowrap transition-colors focus-visible:ring-2 focus-visible:outline-none"
        >
          Sign in
        </button>
        {isAuthModalOpen && (
          <AuthModal
            isOpen={isAuthModalOpen}
            onClose={() => setIsAuthModalOpen(false)}
            defaultMode={authModalMode}
            onAuthSuccess={() => {
              if (isSafeInternalPath(postAuthRedirectPath)) {
                router.push(postAuthRedirectPath);
              }
            }}
            callbackUrl={
              isSafeInternalPath(postAuthRedirectPath) ? postAuthRedirectPath : undefined
            }
          />
        )}
      </>
    );
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-controls={menuId}
        aria-label="Open account menu"
        className="hover:bg-surface-subtle focus-visible:ring-focus-ring flex items-center gap-2 rounded-lg px-3 py-2 transition-colors focus-visible:ring-2 focus-visible:outline-none"
      >
        {user.image ? (
          <img src={user.image} alt={user.name || 'User'} className="h-8 w-8 rounded-full" />
        ) : (
          <div className="bg-accent text-on-accent flex h-8 w-8 items-center justify-center rounded-full">
            <User className="h-5 w-5" />
          </div>
        )}
        <span className="text-foreground-secondary hidden max-w-48 truncate text-sm font-medium sm:block">
          {user.name || user.email}
        </span>
        <ChevronDown className="text-foreground-muted h-4 w-4" />
      </button>

      {isOpen && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
            aria-label="Close user menu"
          />
          <div
            id={menuId}
            role="menu"
            className="border-border bg-surface absolute right-0 z-60 mt-2 w-56 rounded-lg border shadow-lg"
          >
            {/* User Info Header */}
            <div className="border-border border-b px-4 py-3">
              <p className="text-foreground text-sm font-medium">{user.name || 'User'}</p>
              <p className="text-foreground-muted truncate text-xs">{user.email}</p>
            </div>

            {/* Menu Items */}
            <div className="py-1">
              <Link
                role="menuitem"
                href="/profile"
                onClick={() => setIsOpen(false)}
                className="text-foreground-secondary hover:bg-surface-subtle hover:text-foreground flex items-center gap-3 px-4 py-2 text-sm transition-colors"
              >
                <UserCircle className="h-4 w-4" />
                My Profile
              </Link>

              <Link
                role="menuitem"
                href="/settings"
                onClick={() => setIsOpen(false)}
                className="text-foreground-secondary hover:bg-surface-subtle hover:text-foreground flex items-center gap-3 px-4 py-2 text-sm transition-colors"
              >
                <Settings className="h-4 w-4" />
                Account Settings
              </Link>

              <Link
                role="menuitem"
                href="/?matched=true"
                onClick={() => setIsOpen(false)}
                className="text-foreground-secondary hover:bg-surface-subtle hover:text-foreground flex items-center gap-3 px-4 py-2 text-sm transition-colors"
              >
                <Sparkles className="h-4 w-4" />
                My Matches
              </Link>

              <Link
                role="menuitem"
                href="/profile#notifications"
                onClick={() => setIsOpen(false)}
                className="text-foreground-secondary hover:bg-surface-subtle hover:text-foreground flex items-center gap-3 px-4 py-2 text-sm transition-colors"
              >
                <Bell className="h-4 w-4" />
                Notifications
                {unreadCount > 0 && (
                  <span className="bg-accent text-on-accent ml-auto inline-flex min-w-5 items-center justify-center rounded-full px-1.5 py-0.5 text-[10px] font-semibold">
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                )}
              </Link>
            </div>

            {/* Divider */}
            <div className="border-border border-t" />

            {/* Sign Out */}
            <div className="py-1">
              {logoutError && (
                <p role="alert" className="text-danger px-4 py-2 text-xs">
                  {logoutError}
                </p>
              )}
              <button
                type="button"
                role="menuitem"
                onClick={handleLogout}
                className="text-danger hover:bg-surface-subtle flex w-full items-center gap-3 px-4 py-2 text-sm transition-colors"
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
