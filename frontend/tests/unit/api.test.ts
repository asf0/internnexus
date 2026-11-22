import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  fetchCategories,
  fetchCompanies,
  fetchJobs,
  fetchLocations,
  fetchRelatedJobs,
  fetchSitemapJobIds,
} from '@/lib/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('job API', () => {
  it('returns validated job-list data', async () => {
    const payload = { items: [], total: 0, page: 1, page_size: 20 };
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(payload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );

    await expect(fetchJobs()).resolves.toEqual(payload);
  });

  it('does not present a failed request as an empty result set', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 503 })));

    await expect(fetchJobs()).rejects.toThrow('Unable to load jobs (503)');
  });

  it('caches facet lists instead of refetching them on every render', async () => {
    // A fresh Response per call: a body can only be consumed once.
    const fetchMock = vi.fn().mockImplementation(
      async () =>
        new Response(JSON.stringify(['Acme']), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
    );
    vi.stubGlobal('fetch', fetchMock);

    await fetchCompanies();
    await fetchCategories();

    for (const [, init] of fetchMock.mock.calls) {
      expect(init).toMatchObject({ next: { revalidate: 3600 } });
      expect(init).not.toHaveProperty('cache', 'no-store');
    }
  });
});

describe('bounded fetch caching', () => {
  const json = (body: unknown) =>
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  it('keeps the job list out of the unbounded Next data cache', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(async () => json({ items: [], total: 0, page: 1, page_size: 20 }));
    vi.stubGlobal('fetch', fetchMock);

    await fetchJobs();

    expect(fetchMock.mock.calls[0][1]).toMatchObject({ cache: 'no-store' });
    expect(fetchMock.mock.calls[0][1]).not.toHaveProperty('next');
  });

  it('keeps the location facets out of the unbounded Next data cache', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => json([]));
    vi.stubGlobal('fetch', fetchMock);

    await fetchLocations();

    expect(fetchMock.mock.calls[0][1]).toMatchObject({ cache: 'no-store' });
    expect(fetchMock.mock.calls[0][1]).not.toHaveProperty('next');
  });

  it('does not cache related jobs per job id', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(async () => json({ items: [], total: 0, page: 1, page_size: 20 }));
    vi.stubGlobal('fetch', fetchMock);

    await fetchRelatedJobs('job-1');

    expect(fetchMock.mock.calls[0][1]).toMatchObject({ cache: 'no-store' });
    expect(fetchMock.mock.calls[0][1]).not.toHaveProperty('next');
  });
});

describe('sitemap job IDs', () => {
  const sitemapResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  it('fetches a slice in a single request', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      sitemapResponse({
        items: [{ id: '00000000-0000-0000-0000-000000000001', posted_at: '2026-07-03T00:00:00Z' }],
        total: 245644,
      })
    );
    vi.stubGlobal('fetch', fetchMock);

    const result = await fetchSitemapJobIds({ limit: 50000, offset: 100000 });

    expect(result.total).toBe(245644);
    expect(result.items).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/jobs/sitemap-ids?limit=50000&offset=100000'),
      ...([] as unknown[])
    );
  });

  it('defaults offset to zero', async () => {
    const fetchMock = vi.fn().mockResolvedValue(sitemapResponse({ items: [], total: 0 }));
    vi.stubGlobal('fetch', fetchMock);

    await fetchSitemapJobIds({ limit: 0 });

    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('limit=0&offset=0'));
  });

  it('does not opt out of the data cache, so the sitemap route stays static', async () => {
    const fetchMock = vi.fn().mockResolvedValue(sitemapResponse({ items: [], total: 0 }));
    vi.stubGlobal('fetch', fetchMock);

    await fetchSitemapJobIds({ limit: 10 });

    const init = fetchMock.mock.calls[0][1];
    expect(init?.cache).toBeUndefined();
  });

  it('throws rather than returning a partial sitemap', async () => {
    // The old paginating implementation returned whatever it had collected
    // when the backend rate-limited it, silently publishing a truncated
    // sitemap. A throw makes ISR keep serving the last good one instead.
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 429 })));

    await expect(fetchSitemapJobIds({ limit: 50000 })).rejects.toThrow(
      'Unable to load sitemap job ids (429)'
    );
  });

  it('rejects a response that does not match the schema', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sitemapResponse({ items: [{}], total: 1 })));

    await expect(fetchSitemapJobIds({ limit: 1 })).rejects.toThrow();
  });
});
