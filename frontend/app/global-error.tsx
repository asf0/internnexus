'use client';

import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import Link from 'next/link';

interface GlobalErrorProps {
  readonly error: Error & { readonly digest?: string };
  readonly reset: () => void;
}

/**
 * Global Error Handler
 *
 * Next.js 15+ global-error.tsx catches errors in the root layout
 * This is the last line of defense for uncaught errors
 */
export default function GlobalError({ error, reset }: GlobalErrorProps) {
  return (
    <html lang="en">
      <body className="dark:bg-md-surface flex min-h-screen flex-col items-center justify-center bg-slate-50 p-4">
        <div className="dark:border-md-outline-variant dark:bg-md-surface-container-low w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-lg">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-red-100 dark:bg-red-900">
            <AlertTriangle className="h-10 w-10 text-red-600 dark:text-red-300" />
          </div>

          <h1 className="dark:text-md-on-surface mb-2 text-3xl font-bold text-slate-900">
            Critical Error
          </h1>

          <p className="dark:text-md-on-surface-variant mb-6 text-slate-600">
            A critical error has occurred. Our team has been notified.
          </p>

          {error.digest && (
            <p className="dark:text-md-on-surface-variant mb-6 text-xs text-slate-400">
              Error ID: {error.digest}
            </p>
          )}

          <div className="flex flex-col gap-3">
            <button
              onClick={reset}
              className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700"
            >
              <RefreshCw className="h-4 w-4" />
              Try Again
            </button>

            <Link
              href="/"
              className="dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-6 py-3 font-medium text-slate-700 transition-colors hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              <Home className="h-4 w-4" />
              Back to Home
            </Link>
          </div>

          {/* Show error details in development */}
          {process.env.NODE_ENV === 'development' && (
            <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-left dark:border-red-800 dark:bg-red-950">
              <p className="mb-2 font-semibold text-red-800 dark:text-red-200">
                Error Details (Development Only):
              </p>
              <pre className="overflow-x-auto text-xs text-red-700 dark:text-red-300">
                <code>{error.message}</code>
              </pre>
              {error.stack && (
                <pre className="mt-2 overflow-x-auto text-xs text-red-600 dark:text-red-400">
                  <code>{error.stack}</code>
                </pre>
              )}
            </div>
          )}
        </div>
      </body>
    </html>
  );
}
