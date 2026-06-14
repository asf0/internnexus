'use client';

import { signOut } from 'next-auth/react';
import { User, LogOut, ChevronDown, Settings, UserCircle, Sparkles, Bell } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { AuthModal } from '@/components/auth';
import { useRouter } from 'next/navigation';

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

function isSafeInternalPath(path: string | undefined): path is string {
  return !!path && path.startsWith('/') && !path.startsWith('//');
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
  const hasAutoOpened = useRef(false);
  const router = useRouter();

  useEffect(() => {
    if (!user && autoOpenAuthModal && !hasAutoOpened.current) {
      hasAutoOpened.current = true;
      setAuthModalMode('login');
      setIsAuthModalOpen(true);
    }
  }, [user, autoOpenAuthModal]);

  if (!user) {
    return (
      <>
        <button
          onClick={() => {
            setAuthModalMode('login');
            setIsAuthModalOpen(true);
          }}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          Sign in
        </button>
        <AuthModal
          isOpen={isAuthModalOpen}
          onClose={() => setIsAuthModalOpen(false)}
          defaultMode={authModalMode}
          onAuthSuccess={() => {
            if (isSafeInternalPath(postAuthRedirectPath)) {
              router.push(postAuthRedirectPath);
            }
          }}
          callbackUrl={isSafeInternalPath(postAuthRedirectPath) ? postAuthRedirectPath : undefined}
        />
      </>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="dark:hover:bg-md-surface-container-high flex items-center gap-2 rounded-md px-3 py-1.5 transition-colors hover:bg-slate-100"
      >
        {user.image ? (
          <img src={user.image} alt={user.name || 'User'} className="h-8 w-8 rounded-full" />
        ) : (
          <div className="bg-md-primary flex h-8 w-8 items-center justify-center rounded-full">
            <User className="h-5 w-5 text-white" />
          </div>
        )}
        <span className="dark:text-md-on-surface hidden text-sm font-medium text-slate-700 sm:block">
          {user.name || user.email}
        </span>
        <ChevronDown className="h-4 w-4 text-slate-500" />
      </button>

      {isOpen && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
            aria-label="Close user menu"
          />
          <div className="dark:bg-md-surface-container dark:border-md-outline-variant ring-opacity-5 absolute right-0 z-60 mt-2 w-56 rounded-md border border-slate-200 bg-white shadow-lg ring-1 ring-black">
            {/* User Info Header */}
            <div className="dark:border-md-outline-variant border-b border-slate-200 px-4 py-3">
              <p className="dark:text-md-on-surface text-sm font-medium text-slate-900">
                {user.name || 'User'}
              </p>
              <p className="dark:text-md-on-surface-variant truncate text-xs text-slate-500">
                {user.email}
              </p>
            </div>

            {/* Menu Items */}
            <div className="py-1">
              <Link
                href="/profile"
                onClick={() => setIsOpen(false)}
                className="dark:text-md-on-surface dark:hover:bg-md-surface-container-high flex items-center gap-3 px-4 py-2 text-sm text-slate-700 transition-colors hover:bg-slate-100"
              >
                <UserCircle className="h-4 w-4" />
                My Profile
              </Link>

              <Link
                href="/settings"
                onClick={() => setIsOpen(false)}
                className="dark:text-md-on-surface dark:hover:bg-md-surface-container-high flex items-center gap-3 px-4 py-2 text-sm text-slate-700 transition-colors hover:bg-slate-100"
              >
                <Settings className="h-4 w-4" />
                Account Settings
              </Link>

              <Link
                href="/?matched=true"
                onClick={() => setIsOpen(false)}
                className="dark:text-md-on-surface dark:hover:bg-md-surface-container-high flex items-center gap-3 px-4 py-2 text-sm text-slate-700 transition-colors hover:bg-slate-100"
              >
                <Sparkles className="h-4 w-4" />
                My Matches
              </Link>

              <Link
                href="/profile#notifications"
                onClick={() => setIsOpen(false)}
                className="dark:text-md-on-surface dark:hover:bg-md-surface-container-high flex items-center gap-3 px-4 py-2 text-sm text-slate-700 transition-colors hover:bg-slate-100"
              >
                <Bell className="h-4 w-4" />
                Notifications
                {unreadCount > 0 && (
                  <span className="ml-auto inline-flex min-w-5 items-center justify-center rounded-full bg-blue-600 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                )}
              </Link>
            </div>

            {/* Divider */}
            <div className="dark:border-md-outline-variant border-t border-slate-200" />

            {/* Sign Out */}
            <div className="py-1">
              <button
                onClick={() => {
                  setIsOpen(false);
                  signOut({ callbackUrl: '/' });
                }}
                className="dark:hover:bg-md-surface-container-high flex w-full items-center gap-3 px-4 py-2 text-sm text-red-600 transition-colors hover:bg-slate-100 dark:text-red-400"
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
