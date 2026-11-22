import { afterEach, describe, expect, it, vi } from 'vitest';

import { fetchPublicJobDetail } from '@/lib/public-job-detail';

const job = {
  id: '75079d3a-4ffb-4ffb-9340-8f74cdfe73bf',
  source: 'manual',
  title: 'Software Engineering Intern',
  company: 'Example Co',
  location: 'Remote',
  city: null,
  state: null,
  country: 'US',
  apply_url: 'https://example.com/apply',
  job_category: null,
  job_type: 'internship',
  work_mode: 'remote',
  posted_at: null,
  is_active: true,
  description_html: '<p>Safe description</p>',
  description_truncated: false,
};

describe('fetchPublicJobDetail', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('uses a per-job tagged 30-minute fetch cache for validated public data', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(job), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchPublicJobDetail(job.id)).resolves.toEqual(job);
    expect(fetchMock).toHaveBeenCalledWith(
      `http://localhost:8000/jobs/${job.id}`,
      expect.objectContaining({
        next: { revalidate: 1800, tags: [`job:${job.id}`] },
      })
    );
  });

  it('keeps unavailable jobs out of the cacheable success payload', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 404 }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchPublicJobDetail(job.id)).resolves.toBeNull();
  });
});
