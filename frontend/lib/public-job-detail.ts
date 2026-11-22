import 'server-only';

import { BACKEND_URL } from './config';
import { JobDetailSchema } from './schemas';
import { fetchRelatedJobs } from './api';
import type { JobDetail } from './types/job';

const JOB_DETAIL_REVALIDATE_SECONDS = 30 * 60;
const BACKEND_ERROR_RETRY_DELAY_MS = 250;

/**
 * Fetches the anonymous public representation of one job. This intentionally
 * has no request-specific inputs, which makes its Data Cache entry safe to
 * share between visitors.
 */
export async function fetchPublicJobDetail(jobId: string): Promise<JobDetail | null> {
  const load = async (): Promise<Response> =>
    fetch(`${BACKEND_URL}/jobs/${jobId}`, {
      next: {
        revalidate: JOB_DETAIL_REVALIDATE_SECONDS,
        tags: [`job:${jobId}`],
      },
    });

  let response = await load();

  // A backend 5xx is usually a transient deploy/restart, not a content
  // verdict. One quick retry keeps the render from surfacing an error shell
  // that crawlers record as a soft 404.
  if (response.status >= 500) {
    await new Promise((resolve) => setTimeout(resolve, BACKEND_ERROR_RETRY_DELAY_MS));
    response = await load();
  }

  // Invalid and unavailable job URLs should continue to render as 404s. Do
  // not cache failure responses: an admin/pipeline change may make the job
  // available before the next request.
  if (response.status >= 400 && response.status < 500) return null;
  if (!response.ok) throw new Error(`Unable to load job details (${response.status})`);

  return JobDetailSchema.parse(await response.json());
}

export { fetchRelatedJobs };
