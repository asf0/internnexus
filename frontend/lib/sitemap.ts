/**
 * Shared sitemap chunking maths.
 *
 * Lives here rather than in `app/sitemap.ts` because Next's metadata route
 * loader rewrites that file's exports; importing helpers out of it from
 * `app/robots.ts` would depend on that transform's internals.
 */

import type { MetadataRoute } from 'next';
import { categorySlug, companySlug } from './hub-slugs';

/** The sitemap protocol caps a single file at 50,000 URLs. */
export const URLS_PER_SITEMAP = 50000;

/** Static, non-job pages. Always emitted in chunk 0. */
export function buildStaticRoutes(
  baseUrl: string,
  hubs: { companies: string[]; categories: string[] } = { companies: [], categories: [] }
): MetadataRoute.Sitemap {
  const routes: MetadataRoute.Sitemap = [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
    {
      url: `${baseUrl}/about`,
      lastModified: new Date('2026-07-03'),
      changeFrequency: 'monthly',
      priority: 0.4,
    },
    {
      url: `${baseUrl}/privacy`,
      lastModified: new Date('2026-07-03'),
      changeFrequency: 'monthly',
      priority: 0.3,
    },
    {
      url: `${baseUrl}/terms`,
      lastModified: new Date('2026-07-03'),
      changeFrequency: 'monthly',
      priority: 0.3,
    },
    {
      url: `${baseUrl}/companies`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.7,
    },
    {
      url: `${baseUrl}/categories`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.7,
    },
  ];

  for (const company of hubs.companies) {
    routes.push({
      url: `${baseUrl}/companies/${companySlug(company)}`,
      changeFrequency: 'daily',
      priority: 0.6,
    });
  }
  for (const category of hubs.categories) {
    routes.push({
      url: `${baseUrl}/categories/${categorySlug(category)}`,
      changeFrequency: 'daily',
      priority: 0.6,
    });
  }
  return routes;
}

/**
 * Number of chunks needed to cover every job plus the static pages.
 *
 * Static pages share chunk 0 with jobs, and that shared budget is what keeps
 * every file at or under the 50,000-URL protocol limit. Counting them here is
 * why `total` alone would under-estimate and push chunk 0 over.
 */
export function sitemapChunkCount(total: number, staticCount = 0): number {
  if (!Number.isFinite(total) || total <= 0) return 1;
  return Math.ceil((total + staticCount) / URLS_PER_SITEMAP);
}

/**
 * Job slice for one chunk.
 *
 * Chunk 0 spends part of its budget on the static pages, so it takes fewer
 * jobs and starts at offset 0. Later chunks start after the static-shifted
 * boundary. The two halves must agree or a chunk will straddle another's
 * range, duplicating some jobs and dropping others.
 */
export function sitemapChunkSlice(id: number, staticCount = 0): { offset: number; limit: number } {
  if (id <= 0) {
    return { offset: 0, limit: URLS_PER_SITEMAP - staticCount };
  }
  return { offset: id * URLS_PER_SITEMAP - staticCount, limit: URLS_PER_SITEMAP };
}

/** Public URLs of every generated chunk, for robots.txt to advertise. */
export function sitemapChunkUrls(total: number, baseUrl: string, staticCount = 0): string[] {
  return Array.from(
    { length: sitemapChunkCount(total, staticCount) },
    (_, id) => `${baseUrl}/sitemap/${id}.xml`
  );
}
