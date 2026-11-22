'use client';

import { ErrorFallback } from '@/components/common/ErrorFallback';

interface HomeErrorProps {
  readonly error: Error & { digest?: string };
  readonly reset: () => void;
}

export default function HomeError({ error, reset }: HomeErrorProps) {
  return <ErrorFallback error={error} reset={reset} homeLabel="Reload job search" />;
}
