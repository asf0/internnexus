import type { Metadata } from 'next';
import Link from 'next/link';
import { fetchCompanies } from '@/lib/api';
import { BASE_URL } from '@/lib/config';
import { SITE_NAME, siteOpenGraphImage } from '@/lib/seo';
import { companySlug } from '@/lib/hub-slugs';
import { buildCompanyDirectory, companyDirectoryHref } from '@/lib/company-directory';

export const metadata: Metadata = {
  title: 'Browse companies hiring interns & entry-level roles',
  description:
    'Every company with open internships and entry-level jobs on InternNexus. Pick a company to see its current openings.',
  alternates: {
    canonical: `${BASE_URL}/companies`,
  },
  openGraph: {
    title: `Browse companies | ${SITE_NAME}`,
    description: 'Every company with open internships and entry-level jobs on InternNexus.',
    url: `${BASE_URL}/companies`,
    images: siteOpenGraphImage(),
  },
};

// Rendered on demand: prerendering here would bake an empty directory into
// the build, which runs without a backend. The facet fetch below still hits
// its one-hour Data Cache, so the per-request cost stays trivial.
export const dynamic = 'force-dynamic';

interface CompaniesPageProps {
  searchParams: Promise<{ page?: string; q?: string }>;
}

const paginationLinkClass =
  'border-border bg-surface hover:bg-surface-subtle rounded-lg border px-4 py-2 text-sm font-medium transition-colors';

export default async function CompaniesPage({ searchParams }: CompaniesPageProps) {
  const params = await searchParams;
  const companies = await fetchCompanies();
  const { items, total, page, totalPages, query } = buildCompanyDirectory(companies, params);
  const hasCompanies = companies.length > 0;

  return (
    <div className="space-y-6">
      <header className="space-y-3">
        <h1 className="text-foreground text-3xl font-semibold">Companies</h1>
        <p className="text-foreground-secondary text-sm">
          {!hasCompanies
            ? 'Company listings are temporarily unavailable. Please check back soon.'
            : query
              ? `${total} ${total === 1 ? 'company matches' : 'companies match'} “${query}”.`
              : `${total} companies with current openings.`}
        </p>
        {hasCompanies && (
          <form action="/companies" method="get" className="flex flex-wrap items-center gap-2">
            <input
              type="search"
              name="q"
              defaultValue={query}
              placeholder="Search companies..."
              aria-label="Search companies"
              className="border-border bg-surface text-foreground focus:border-accent w-full max-w-sm rounded-lg border px-3 py-2 text-sm outline-none"
            />
            <button
              type="submit"
              className="bg-accent text-on-accent rounded-lg px-4 py-2 text-sm font-medium"
            >
              Search
            </button>
            {query && (
              <Link
                href="/companies"
                className="text-foreground-secondary hover:text-foreground text-sm underline"
              >
                Clear
              </Link>
            )}
          </form>
        )}
      </header>

      {hasCompanies && items.length === 0 && (
        <p className="text-foreground-secondary text-sm">
          No companies match “{query}”. Try a different name or{' '}
          <Link href="/companies" className="underline">
            clear the search
          </Link>
          .
        </p>
      )}

      {items.length > 0 && (
        <>
          <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((company) => (
              <li key={company}>
                <Link
                  href={`/companies/${companySlug(company)}`}
                  className="border-border bg-surface hover:bg-surface-subtle block rounded-lg border px-4 py-3 text-sm font-medium transition-colors"
                >
                  {company}
                </Link>
              </li>
            ))}
          </ul>

          {totalPages > 1 && (
            <nav
              aria-label="Company directory pages"
              className="flex flex-wrap items-center justify-between gap-3"
            >
              {page > 1 ? (
                <Link href={companyDirectoryHref(page - 1, query)} className={paginationLinkClass}>
                  Previous
                </Link>
              ) : (
                <span />
              )}
              <span className="text-foreground-muted text-xs">
                Page {page} of {totalPages}
              </span>
              {page < totalPages ? (
                <Link href={companyDirectoryHref(page + 1, query)} className={paginationLinkClass}>
                  Next
                </Link>
              ) : (
                <span />
              )}
            </nav>
          )}
        </>
      )}
    </div>
  );
}
