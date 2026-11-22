import { MetadataRoute } from 'next';
import { fetchCompanies, fetchCategories, fetchSitemapJobIds } from '../lib/api';
import { BASE_URL } from '../lib/config';
import { buildStaticRoutes, sitemapChunkCount, sitemapChunkSlice } from '../lib/sitemap';
import { categorySlug, companySlug } from '../lib/hub-slugs';

// Sitemaps are regenerated once a day rather than on every crawler hit. The
// route must stay statically cacheable for this to apply, so nothing it calls
// may use `cache: 'no-store'`.
export const revalidate = 86400;

// Chunks that generateSitemaps did not enumerate are still served, generated
// on first request and then cached like any other. This is what lets the
// image build without a backend; see the fallback in generateSitemaps.
export const dynamicParams = true;

// Facet fetches return [] on backend failure, so the hub portion of chunk 0
// degrades to the static pages alone instead of failing the whole sitemap.
const STATIC_ROUTES = buildStaticRoutes(BASE_URL);

export async function generateSitemaps(): Promise<{ id: number }[]> {
  try {
    // limit=0 asks the backend for the count alone, skipping the id query.
    const { total } = await fetchSitemapJobIds({ limit: 0 });
    return Array.from({ length: sitemapChunkCount(total, STATIC_ROUTES.length) }, (_, id) => ({
      id,
    }));
  } catch {
    // `next build` runs inside `docker build`, where the backend container is
    // not on the network. Prerendering nothing keeps the build green;
    // dynamicParams then generates each chunk on its first request instead.
    return [];
  }
}

export default async function sitemap(props: {
  id: Promise<string>;
}): Promise<MetadataRoute.Sitemap> {
  const id = Number(await props.id);
  // Chunk 0 also carries the static pages, so it fetches fewer jobs and the
  // remaining chunks are offset past that shared budget. See sitemapChunkSlice.
  const { offset, limit } = sitemapChunkSlice(id, STATIC_ROUTES.length);

  if (id !== 0) {
    const { items } = await fetchSitemapJobIds({ limit, offset });
    return items.map((job) => ({
      url: `${BASE_URL}/jobs/${job.id}`,
      // The job's own posting date, not `new Date()`. Stamping today onto every
      // entry claims the whole catalogue changed daily, which teaches crawlers
      // to ignore the field.
      lastModified: job.posted_at ? new Date(job.posted_at) : undefined,
      changeFrequency: 'weekly',
      priority: 0.8,
    }));
  }

  // Facet fetches resolve to [] on any failure, connection refused included,
  // so chunk 0 always publishes: the hub URLs drop out and return once the
  // backend is reachable again.
  const [{ items }, companies, categories] = await Promise.all([
    fetchSitemapJobIds({ limit, offset }),
    fetchCompanies().catch(() => [] as string[]),
    fetchCategories().catch(() => [] as string[]),
  ]);

  const jobUrls: MetadataRoute.Sitemap = items.map((job) => ({
    url: `${BASE_URL}/jobs/${job.id}`,
    lastModified: job.posted_at ? new Date(job.posted_at) : undefined,
    changeFrequency: 'weekly',
    priority: 0.8,
  }));

  return [
    ...buildStaticRoutes(BASE_URL, {
      companies: companies.map(companySlug),
      categories: categories.map(categorySlug),
    }),
    ...jobUrls,
  ];
}
