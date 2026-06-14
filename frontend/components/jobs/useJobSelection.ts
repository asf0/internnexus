'use client';

import { useMemo, useCallback } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { generateJobSlug, findJobBySlug } from '@/lib/utils';
import type { Job } from '@/lib/types/job';

export function useJobSelection(jobs: Job[]) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const selectedSlug = searchParams.get('selected');

  const selectedJob = useMemo(() => {
    if (!selectedSlug) return null;
    return findJobBySlug(jobs, selectedSlug) || null;
  }, [selectedSlug, jobs]);

  const handleJobClick = useCallback(
    (job: Job) => {
      const slug = generateJobSlug(job.title, job.company, job.id);
      const params = new URLSearchParams(searchParams.toString());
      params.set('selected', slug);
      router.push(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [searchParams, router, pathname]
  );

  const handleClose = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('selected');
    const newUrl = params.toString() ? `${pathname}?${params.toString()}` : pathname;
    router.push(newUrl, { scroll: false });
  }, [searchParams, router, pathname]);

  const buildPageUrl = useCallback(
    (page: number) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('page', page.toString());
      params.delete('selected');
      return `/?${params.toString()}`;
    },
    [searchParams]
  );

  return {
    selectedSlug,
    selectedJob,
    handleJobClick,
    handleClose,
    buildPageUrl,
  };
}
