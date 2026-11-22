'use client';

import './globals.css';

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
      <body className="bg-canvas text-foreground flex min-h-screen flex-col items-center justify-center p-4">
        <div className="border-border bg-surface w-full max-w-md rounded-2xl border p-8 text-center shadow-lg">
          <div className="dark:bg-danger/15 mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-red-100">
            <AlertTriangle className="dark:text-danger h-10 w-10 text-red-600" />
          </div>

          <h1 className="text-foreground mb-2 text-3xl font-bold">
            We couldn&apos;t load InternNexus
          </h1>

          <p className="text-foreground-secondary mb-6">
            Try loading the page again. If the problem continues, return to the job search.
          </p>

          {error.digest && (
            <p className="text-foreground-muted mb-6 text-xs">Error ID: {error.digest}</p>
          )}

          <div className="flex flex-col gap-3">
            <button
              onClick={reset}
              className="bg-accent text-on-accent hover:bg-accent-hover focus-visible:ring-focus-ring flex items-center justify-center gap-2 rounded-lg px-6 py-3 font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none"
            >
              <RefreshCw className="h-4 w-4" />
              Try Again
            </button>

            <Link
              href="/"
              className="border-border bg-surface text-foreground-secondary hover:bg-surface-subtle focus-visible:ring-focus-ring flex items-center justify-center gap-2 rounded-lg border px-6 py-3 font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none"
            >
              <Home className="h-4 w-4" />
              Back to Home
            </Link>
          </div>

          {/* Show error details in development */}
          {process.env.NODE_ENV === 'development' && (
            <div className="dark:border-danger/40 dark:bg-surface-inset mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-left">
              <p className="dark:text-danger mb-2 font-semibold text-red-800">
                Error Details (Development Only):
              </p>
              <pre className="dark:text-danger overflow-x-auto text-xs text-red-700">
                <code>{error.message}</code>
              </pre>
              {error.stack && (
                <pre className="dark:text-danger mt-2 overflow-x-auto text-xs text-red-600">
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
