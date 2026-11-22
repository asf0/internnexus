import { beforeEach, describe, expect, it, vi } from 'vitest';

const { revalidateTag } = vi.hoisted(() => ({ revalidateTag: vi.fn() }));
vi.mock('next/cache', () => ({ revalidateTag }));

import { POST } from '@/app/api/internal/job-cache/revalidate/route';

const secret = 'test-job-cache-revalidation-secret';
const jobId = '75079d3a-4ffb-4ffb-9340-8f74cdfe73bf';

describe('job-cache revalidation route', () => {
  beforeEach(() => {
    process.env.JOB_CACHE_REVALIDATION_SECRET = secret;
    revalidateTag.mockReset();
  });

  it('requires its bearer secret', async () => {
    const response = await POST(
      new Request('http://localhost/api/internal/job-cache/revalidate', { method: 'POST' })
    );
    expect(response.status).toBe(401);
    expect(revalidateTag).not.toHaveBeenCalled();
  });

  it('validates UUID batches and revalidates every unique job tag', async () => {
    const response = await POST(
      new Request('http://localhost/api/internal/job-cache/revalidate', {
        method: 'POST',
        headers: { Authorization: `Bearer ${secret}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_ids: [jobId, jobId] }),
      })
    );

    expect(response.status).toBe(200);
    expect(revalidateTag).toHaveBeenCalledTimes(1);
    expect(revalidateTag).toHaveBeenCalledWith(`job:${jobId}`, 'max');
  });
});
