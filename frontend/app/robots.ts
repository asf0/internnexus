import { MetadataRoute } from 'next';
import { fetchCompanies, fetchCategories, fetchSitemapJobIds } from '../lib/api';
import { BASE_URL } from '../lib/config';
import { buildStaticRoutes, sitemapChunkUrls } from '../lib/sitemap';
import { categorySlug, companySlug } from '../lib/hub-slugs';

// Far shorter than the sitemap's own 24h. `docker build` has no backend, so
// this file is prerendered with the fallback below and would under-advertise
// chunks until its first revalidation. It is a few hundred bytes and one count
// query, so a tight window costs nothing and bounds that staleness to minutes.
export const revalidate = 300;

export default async function robots(): Promise<MetadataRoute.Robots> {
  // `generateSitemaps` publishes at /sitemap/{id}.xml and Next reserves the
  // root /sitemap.xml path, so the index lives at /sitemap-index.xml. Advertise
  // the index first, then each chunk: crawlers that follow a sitemap index get
  // the full set, and the explicit chunk lines keep discovery working even if
  // the index is stale.
  // On failure fall back to 0, which yields chunk 0 alone. That chunk always
  // exists, and the next revalidation lists the rest once the backend is up.
  const [result, companies, categories] = await Promise.all([
    fetchSitemapJobIds({ limit: 0 })
      .then((r) => r.total)
      .catch(() => 0),
    fetchCompanies().catch(() => [] as string[]),
    fetchCategories().catch(() => [] as string[]),
  ]);

  const staticRoutes = buildStaticRoutes(BASE_URL, {
    companies: companies.map(companySlug),
    categories: categories.map(categorySlug),
  });

  return {
    rules: {
      userAgent: '*',
      allow: '/',
      // Authenticated-only areas; nothing here is useful to a crawler and the
      // admin tree redirects to the login modal anyway.
      disallow: ['/admin', '/api/', '/profile', '/settings'],
    },
    sitemap: [
      `${BASE_URL}/sitemap-index.xml`,
      ...sitemapChunkUrls(result, BASE_URL, staticRoutes.length),
    ],
  };
}
