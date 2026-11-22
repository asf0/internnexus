import { describe, expect, it } from 'vitest';
import {
  URLS_PER_SITEMAP,
  sitemapChunkCount,
  sitemapChunkSlice,
  sitemapChunkUrls,
  buildStaticRoutes,
} from '@/lib/sitemap';

const STATIC_COUNT = buildStaticRoutes('https://example.com').length;

describe('sitemap chunking', () => {
  it('stays within the sitemap protocol limit of 50,000 URLs per file', () => {
    expect(URLS_PER_SITEMAP).toBeLessThanOrEqual(50000);
  });

  it('covers every job across the chunk set', () => {
    // 245,644 active jobs plus 4 static routes needs 5 chunks.
    expect(sitemapChunkCount(245644, STATIC_COUNT)).toBe(5);
    const capacity =
      sitemapChunkSlice(0, STATIC_COUNT).limit +
      (sitemapChunkCount(245644, STATIC_COUNT) - 1) * URLS_PER_SITEMAP;
    expect(capacity).toBeGreaterThanOrEqual(245644);
  });

  it('never emits a chunk that exceeds the 50,000-URL limit', () => {
    // An exact multiple is the worst case: chunk 0 carries the static routes
    // on top of a full job budget, which is what pushed the old file to 50,004.
    const total = URLS_PER_SITEMAP * 3 - STATIC_COUNT;
    const chunks = sitemapChunkCount(total, STATIC_COUNT);
    expect(chunks).toBe(3);

    for (let id = 0; id < chunks; id += 1) {
      const { limit } = sitemapChunkSlice(id, STATIC_COUNT);
      const count = id === 0 ? limit + STATIC_COUNT : limit;
      expect(count).toBeLessThanOrEqual(URLS_PER_SITEMAP);
    }
  });

  it('slices jobs contiguously with no gaps or overlaps', () => {
    const total = 120000;
    const chunks = sitemapChunkCount(total + 0, STATIC_COUNT);
    let covered = 0;
    for (let id = 0; id < chunks; id += 1) {
      const { offset, limit } = sitemapChunkSlice(id, STATIC_COUNT);
      expect(offset).toBe(covered);
      covered += limit;
    }
    expect(covered).toBeGreaterThanOrEqual(total);
  });

  it('does not add an empty trailing chunk on an exact multiple', () => {
    expect(sitemapChunkCount(URLS_PER_SITEMAP - STATIC_COUNT, STATIC_COUNT)).toBe(1);
    expect(sitemapChunkCount(URLS_PER_SITEMAP - STATIC_COUNT + 1, STATIC_COUNT)).toBe(2);
  });

  it('always emits at least one chunk', () => {
    // An empty catalogue must still serve the static routes, which live on
    // chunk 0. Zero chunks would mean no sitemap at all.
    expect(sitemapChunkCount(0, STATIC_COUNT)).toBe(1);
    expect(sitemapChunkCount(-1, STATIC_COUNT)).toBe(1);
    expect(sitemapChunkCount(Number.NaN, STATIC_COUNT)).toBe(1);
  });

  it('builds the chunk URLs robots.txt advertises', () => {
    expect(sitemapChunkUrls(120000, 'https://example.com')).toEqual([
      'https://example.com/sitemap/0.xml',
      'https://example.com/sitemap/1.xml',
      'https://example.com/sitemap/2.xml',
    ]);
  });
});

describe('hub routes in the sitemap', () => {
  it('includes hub index and slug pages when facets are provided', () => {
    const routes = buildStaticRoutes('https://example.com', {
      companies: ['Acme Corp', 'Ben'],
      categories: ['software_engineering'],
    });
    const urls = routes.map((route) => route.url);
    expect(urls).toContain('https://example.com/companies');
    expect(urls).toContain('https://example.com/categories');
    expect(urls).toContain('https://example.com/companies/acme-corp');
    expect(urls).toContain('https://example.com/companies/ben');
    expect(urls).toContain('https://example.com/categories/software-engineering');
  });

  it('keeps the base static routes when no facets are provided', () => {
    const withHubs = buildStaticRoutes('https://example.com', {
      companies: ['Ben'],
      categories: [],
    });
    const withoutHubs = buildStaticRoutes('https://example.com');
    expect(withHubs.length).toBe(withoutHubs.length + 1);
  });

  it('counts hub routes in the chunk budget', () => {
    // Many hubs must still be accounted for by sitemapChunkCount: the static
    // count passed to the chunk maths must come from the built routes.
    const routes = buildStaticRoutes('https://example.com', {
      companies: Array.from({ length: 5000 }, (_, i) => `company-${i}`),
      categories: ['a', 'b', 'c'],
    });
    expect(routes.length).toBe(buildStaticRoutes('https://example.com').length + 5003);
    expect(sitemapChunkCount(245644, routes.length)).toBeGreaterThanOrEqual(
      sitemapChunkCount(245644, buildStaticRoutes('https://example.com').length)
    );
  });
});
