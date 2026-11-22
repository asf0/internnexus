import type { Metadata } from 'next';
import { UserMenu } from '@/components/common';
import { Toolbar } from '@/components/toolbar';
import { JobList } from '@/components/jobs';
import { fetchJobs, fetchLocations, fetchCategories } from '@/lib/api';
import { BASE_URL } from '@/lib/config';
import { homeMetadata } from '@/lib/seo';
import Link from 'next/link';
import { auth } from '@/auth';
import { headers } from 'next/headers';
import { toSafeJsonLd } from '@/lib/security/jsonld';
import { fetchHomeState } from '@/app/actions/user';
import { getBackendToken } from '@/lib/auth.server';
import { redirect } from 'next/navigation';

interface HomePageProps {
  searchParams: Promise<{
    page?: string;
    search?: string;
    company?: string;
    location?: string;
    category?: string;
    job_type?: string;
    work_mode?: string;
    posted_within?: string;
    saved_only?: string;
    matched?: string;
    auth?: string;
    callbackUrl?: string;
  }>;
}

export async function generateMetadata({
  searchParams,
}: Readonly<HomePageProps>): Promise<Metadata> {
  return homeMetadata(await searchParams, BASE_URL);
}

export default async function HomePage({ searchParams }: Readonly<HomePageProps>) {
  const params = await searchParams;
  const nonce = (await headers()).get('x-nonce') ?? undefined;
  const parsedPage = Number.parseInt(params.page || '1', 10);
  const currentPage = Number.isInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;
  const isMatched = params.matched === 'true';
  const session = await auth();
  const tokenResult = session?.user ? await getBackendToken() : null;
  const backendToken = tokenResult?.ok ? tokenResult.token : undefined;
  const [homeState, data, locations, categories] = await Promise.all([
    session?.user ? fetchHomeState() : Promise.resolve(null),
    isMatched
      ? Promise.resolve({ items: [], total: 0, page: 1, page_size: 20 })
      : fetchJobs(
          {
            page: currentPage,
            search: params.search,
            company: params.company,
            location: params.location,
            category: params.category,
            job_type: params.job_type,
            work_mode: params.work_mode,
            posted_within: params.posted_within,
            saved_only: params.saved_only,
          },
          backendToken
        ),
    fetchLocations(
      {
        search: params.search,
        company: params.company,
        category: params.category,
        job_type: params.job_type,
        work_mode: params.work_mode,
        posted_within: params.posted_within,
        match_ids: undefined,
        saved_only: params.saved_only,
      },
      backendToken
    ),
    fetchCategories(),
  ]);

  const unreadCount = homeState?.unread_count ?? 0;
  const initialSavedJobIds = homeState?.saved_job_ids ?? [];
  const initialAppliedJobIds = homeState?.applied_job_ids ?? [];

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));

  if (data.total > 0 && currentPage > totalPages) {
    const normalizedParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value) normalizedParams.set(key, value);
    }
    normalizedParams.set('page', totalPages.toString());
    redirect(`/?${normalizedParams.toString()}`);
  }

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: 'Internship Listings',
    numberOfItems: data.total,
    itemListElement: data.items.map((job, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      url: `${BASE_URL}/jobs/${job.id}`,
    })),
  };

  return (
    <div className="space-y-6">
      <script
        suppressHydrationWarning
        nonce={nonce}
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: toSafeJsonLd(jsonLd) }}
      />
      <header className="flex items-center justify-between gap-4">
        <div>
          <Link href="/" className="transition-opacity hover:opacity-80">
            <h1 className="text-foreground text-2xl font-bold tracking-tight">InternNexus</h1>
          </Link>
          <p className="text-foreground-muted text-sm">
            Search current opportunities from company career sites.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <UserMenu
            user={session?.user}
            autoOpenAuthModal={params.auth === 'required'}
            postAuthRedirectPath={params.callbackUrl}
            unreadCount={unreadCount}
          />
        </div>
      </header>

      <Toolbar locations={locations} categories={categories} isAuthenticated={!!session?.user} />

      <JobList
        jobs={data.items}
        total={data.total}
        totalPages={totalPages}
        currentPage={currentPage}
        matched={isMatched}
        isAuthenticated={!!session?.user}
        initialSavedJobIds={initialSavedJobIds}
        initialAppliedJobIds={initialAppliedJobIds}
      />
    </div>
  );
}
