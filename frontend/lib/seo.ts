/**
 * Indexability rules for the public job search homepage.
 *
 * The homepage is one route that also serves every filtered and paginated
 * view through query parameters (`?company=google&page=3`). Those variants
 * are useful to visitors but would explode into effectively infinite
 * duplicate URLs for crawlers, so only the clean first page is indexable.
 * Every other variant canonicalises to the clean homepage and is marked
 * `noindex, follow` so crawlers still traverse its links.
 */

import type { Metadata } from 'next';
import { BASE_URL } from '@/lib/config';

export const SITE_NAME = 'InternNexus';
export const SITE_DESCRIPTION =
  'Search current internships and entry-level roles aggregated from company career sites. Filter by company, location, category, and work mode.';

/**
 * The generated social preview image, served from `app/og/route.tsx`.
 *
 * Referenced explicitly rather than via the `opengraph-image` file convention:
 * a page that defines its own `openGraph` (about, job detail, ...) replaces
 * the whole object, dropping a convention-derived image. An explicit entry in
 * each page's metadata is immune to that.
 */
export const OG_IMAGE_URL = `${BASE_URL}/og`;
export const OG_IMAGE_ALT = 'InternNexus — Search internships and entry-level jobs';
export const OG_IMAGE_WIDTH = 1200;
export const OG_IMAGE_HEIGHT = 630;

export function siteOpenGraphImage(): NonNullable<NonNullable<Metadata['openGraph']>['images']> {
  return [
    {
      url: OG_IMAGE_URL,
      width: OG_IMAGE_WIDTH,
      height: OG_IMAGE_HEIGHT,
      alt: OG_IMAGE_ALT,
    },
  ];
}

/** Query parameters that select a filtered or paginated subset of jobs. */
export const HOME_FILTER_PARAMS = [
  'search',
  'company',
  'location',
  'category',
  'job_type',
  'work_mode',
  'posted_within',
  'saved_only',
  'matched',
] as const;

/** `page` is handled separately: only the first page is canonical. */
const PAGE_PARAM = 'page';

/**
 * True when a request selects something other than the clean first page.
 */
export function hasActiveHomeFilters(searchParams: Record<string, string | undefined>): boolean {
  if (HOME_FILTER_PARAMS.some((key) => Boolean(searchParams[key]))) return true;

  const page = searchParams[PAGE_PARAM];
  return Boolean(page) && Number.parseInt(page as string, 10) > 1;
}

/**
 * Build the homepage metadata for a given set of search parameters.
 *
 * When filters are active the canonical still points at the clean homepage
 * (consolidating signals) and the page is kept out of the index. On the clean
 * homepage `robots` is omitted so the site-wide default applies.
 */
export function homeMetadata(
  searchParams: Record<string, string | undefined>,
  baseUrl: string
): Metadata {
  const filtered = hasActiveHomeFilters(searchParams);

  return {
    alternates: {
      canonical: baseUrl,
    },
    ...(filtered ? { robots: { index: false, follow: true } } : {}),
  };
}

/**
 * Metadata for hub pages (company and category listings).
 *
 * The clean first page is indexable; deeper pages are `noindex, follow` with
 * the canonical pinned to page 1, mirroring the homepage's treatment of
 * paginated variants.
 */
export function hubMetadata(
  hubPath: string,
  page: number,
  title: string,
  description: string
): Metadata {
  const canonical = page > 1 ? `${hubPath}?page=1` : hubPath;

  return {
    title,
    description,
    alternates: {
      canonical: `${BASE_URL}${canonical}`,
    },
    openGraph: {
      title,
      description,
      url: `${BASE_URL}${canonical}`,
      images: siteOpenGraphImage(),
    },
    ...(page > 1 ? { robots: { index: false, follow: true } } : {}),
  };
}
