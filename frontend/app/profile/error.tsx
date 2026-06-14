'use client';

import { ErrorFallback } from '@/components/common/ErrorFallback';

export default function ProfileError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <ErrorFallback error={error} reset={reset} homeHref="/" homeLabel="Go home" />;
}
