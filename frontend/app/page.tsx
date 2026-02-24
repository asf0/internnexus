import { UserMenu } from "@/components/common";
import { Toolbar } from "@/components/toolbar";
import { JobList } from "@/components/jobs";
import { fetchJobs, fetchCompanies, fetchLocations, fetchCategories } from "@/lib/api";
import { BASE_URL } from "../lib/config";
import Link from "next/link";
import { auth } from "@/auth";
import { headers } from "next/headers";
import { toSafeJsonLd } from "@/lib/security/jsonld";
import { fetchUnreadNotificationCount } from "@/app/actions/user";
import { fetchSavedJobIds } from "@/app/actions/user";
import { fetchAppliedJobIds } from "@/app/actions/user";
import { getBackendToken } from "@/lib/auth.server";

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

export default async function HomePage({ searchParams }: HomePageProps) {
  const params = await searchParams;
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  const currentPage = parseInt(params.page || "1", 10);
  const isMatched = params.matched === "true";
  const session = await auth();
  const backendToken = session?.user ? await getBackendToken() : undefined;
  const unreadCount = session?.user ? await fetchUnreadNotificationCount() : 0;
  const initialSavedJobIds = session?.user ? await fetchSavedJobIds() : [];
  const initialAppliedJobIds = session?.user ? await fetchAppliedJobIds() : [];
  
  const [data, companies, locations, categories] = await Promise.all([
    isMatched 
      ? Promise.resolve({ items: [], total: 0, page: 1, page_size: 20 })
      : fetchJobs({ 
          page: currentPage,
          search: params.search,
          company: params.company,
          location: params.location,
          category: params.category,
          job_type: params.job_type,
          work_mode: params.work_mode,
          posted_within: params.posted_within,
          saved_only: params.saved_only,
        }, backendToken),
    fetchCompanies(),
    fetchLocations(),
    fetchCategories(),
  ]);
  
  const totalPages = Math.ceil(data.total / data.page_size);

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    "name": "Internship Listings",
    "numberOfItems": data.total,
    "itemListElement": data.items.map((job, index) => ({
      "@type": "ListItem",
      "position": index + 1,
      "url": `${BASE_URL}/jobs/${job.id}`,
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
      <header className="flex items-center justify-between">
        <div>
          <Link href="/" className="hover:opacity-80 transition-opacity">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                  InternNexus
                </h1>
            </Link>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Find your next job opportunity with InternNexus, the ultimate job discovery and matching platform for students and recent graduates.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <UserMenu
            user={session?.user}
            autoOpenAuthModal={params.auth === "required"}
            postAuthRedirectPath={params.callbackUrl}
            unreadCount={unreadCount}
          />
        </div>
      </header>

      <Toolbar 
        companies={companies} 
        locations={locations} 
        categories={categories}
        isAuthenticated={!!session?.user}
      />

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
