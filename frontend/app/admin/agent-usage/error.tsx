'use client';

import { ErrorFallback } from '@/components/common/ErrorFallback';

export default function McpUsageError({
  error,
  reset,
}: {
  readonly error: Error & { digest?: string };
  readonly reset: () => void;
}) {
  return (
    <ErrorFallback error={error} reset={reset} homeHref="/admin" homeLabel="Admin dashboard" />
  );
}
