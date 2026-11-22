import { fetchCompanies, fetchCategories, fetchSitemapJobIds } from '@/lib/api';
import { BASE_URL } from '@/lib/config';
import { buildStaticRoutes, sitemapChunkCount } from '@/lib/sitemap';
import { categorySlug, companySlug } from '@/lib/hub-slugs';

// Match the per-chunk sitemap's daily cadence; this file is tiny.
export const revalidate = 86400;

/**
 * Sitemap index for the chunked sitemaps published by `app/sitemap.ts`.
 *
 * `generateSitemaps` serves chunks at `/sitemap/{id}.xml`, which leaves no
 * `/sitemap.xml` for crawlers to guess at. `app/sitemap.xml` is reserved by
 * Next's metadata loader, so this index lives at `/sitemap-index.xml` and is
 * advertised from robots.txt.
 */
export async function GET(): Promise<Response> {
  // On failure fall back to one chunk, the always-present chunk 0. The next
  // revalidation lists the rest once the backend is reachable.
  const [total, companies, categories] = await Promise.all([
    fetchSitemapJobIds({ limit: 0 })
      .then((r) => r.total)
      .catch(() => 0),
    fetchCompanies().catch(() => [] as string[]),
    fetchCategories().catch(() => [] as string[]),
  ]);

  const staticCount = buildStaticRoutes(BASE_URL, {
    companies: companies.map(companySlug),
    categories: categories.map(categorySlug),
  }).length;

  const lastmod = new Date().toISOString();
  const entries = Array.from(
    { length: sitemapChunkCount(total, staticCount) },
    (_, id) =>
      `  <sitemap>\n    <loc>${BASE_URL}/sitemap/${id}.xml</loc>\n    <lastmod>${lastmod}</lastmod>\n  </sitemap>`
  ).join('\n');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${entries}
</sitemapindex>
`;

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml',
      'Cache-Control': 'public, max-age=0, must-revalidate',
    },
  });
}
