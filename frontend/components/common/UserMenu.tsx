"use client"

import { signOut } from "next-auth/react"
import { User, LogOut, ChevronDown, Settings, UserCircle } from "lucide-react"
import { useState } from "react"
import Link from "next/link"
import { AuthModal } from "@/components/auth"

interface UserMenuProps {
  user?: { name?: string | null; email?: string | null; image?: string | null } | null
}

export default function UserMenu({ user }: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)
  const [authModalMode, setAuthModalMode] = useState<"login" | "register">("login")

  if (!user) {
    return (
      <>
        <button
          onClick={() => {
            setAuthModalMode("login")
            setIsAuthModalOpen(true)
          }}
          className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
        >
          Sign in
        </button>
        <AuthModal
          isOpen={isAuthModalOpen}
          onClose={() => setIsAuthModalOpen(false)}
          defaultMode={authModalMode}
        />
      </>
    )
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-md-surface-container-high transition-colors"
      >
        {user.image ? (
          <img
            src={user.image}
            alt={user.name || "User"}
            className="h-8 w-8 rounded-full"
          />
        ) : (
          <div className="h-8 w-8 rounded-full bg-md-primary flex items-center justify-center">
            <User className="h-5 w-5 text-white" />
          </div>
        )}
        <span className="text-sm font-medium text-slate-700 dark:text-md-on-surface hidden sm:block">
          {user.name || user.email}
        </span>
        <ChevronDown className="h-4 w-4 text-slate-500" />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white dark:bg-md-surface-container border border-slate-200 dark:border-md-outline-variant ring-1 ring-black ring-opacity-5 z-60">
            {/* User Info Header */}
            <div className="px-4 py-3 border-b border-slate-200 dark:border-md-outline-variant">
              <p className="text-sm font-medium text-slate-900 dark:text-md-on-surface">
                {user.name || "User"}
              </p>
              <p className="text-xs text-slate-500 dark:text-md-on-surface-variant truncate">
                {user.email}
              </p>
            </div>

            {/* Menu Items */}
            <div className="py-1">
              <Link
                href="/profile"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 dark:text-md-on-surface hover:bg-slate-100 dark:hover:bg-md-surface-container-high transition-colors"
              >
                <UserCircle className="h-4 w-4" />
                My Profile
              </Link>

              <Link
                href="/settings"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 dark:text-md-on-surface hover:bg-slate-100 dark:hover:bg-md-surface-container-high transition-colors"
              >
                <Settings className="h-4 w-4" />
                Account Settings
              </Link>
            </div>

            {/* Divider */}
            <div className="border-t border-slate-200 dark:border-md-outline-variant" />

            {/* Sign Out */}
            <div className="py-1">
              <button
                onClick={() => {
                  setIsOpen(false)
                  signOut({ callbackUrl: "/" })
                }}
                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-slate-100 dark:hover:bg-md-surface-container-high transition-colors"
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
