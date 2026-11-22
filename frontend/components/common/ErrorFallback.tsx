'use client';

import { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui';

interface ErrorFallbackProps {
  readonly error: Error & { digest?: string };
  readonly reset: () => void;
  readonly homeHref?: string;
  readonly homeLabel?: string;
}

export function ErrorFallback({
  error,
  reset,
  homeHref = '/',
  homeLabel = 'Go home',
}: ErrorFallbackProps) {
  useEffect(() => {
    if (process.env.NODE_ENV !== 'production') {
      console.error(error);
    }
  }, [error]);

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center p-6 text-center">
      <AlertTriangle className="text-warning mb-4 h-12 w-12" />
      <h2 className="text-foreground mb-2 text-xl font-semibold">Something went wrong</h2>
      <p className="text-foreground-secondary mb-6 max-w-md">
        We couldn&apos;t load this page. You can try again or navigate somewhere safe.
      </p>
      {process.env.NODE_ENV !== 'production' && error.digest && (
        <p className="text-foreground-muted mb-4 font-mono text-xs">Error digest: {error.digest}</p>
      )}
      <div className="flex flex-wrap justify-center gap-3">
        <Button onClick={reset}>Try again</Button>
        <Button variant="secondary" onClick={() => (window.location.href = homeHref)}>
          {homeLabel}
        </Button>
      </div>
    </div>
  );
}
