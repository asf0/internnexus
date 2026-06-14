'use client';

import { ErrorFallback } from '@/components/common/ErrorFallback';

export default function AdminUsersError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <ErrorFallback error={error} reset={reset} homeHref="/admin" homeLabel="Admin dashboard" />
  );
}
