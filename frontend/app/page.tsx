import UserMenu from "../components/UserMenu";
import Toolbar from "../components/Toolbar";
import JobList from "../components/JobList";
import { fetchJobs, fetchCompanies, fetchLocations, fetchCategories } from "../lib/api";
import { BASE_URL } from "../lib/config";
import Link from "next/link";
import { auth } from "@/auth";

interface HomePageProps {
  searchParams: Promise<{ 
    page?: string;
    search?: string;
    company?: string;
    location?: string;
    category?: string;
    visa_sponsored?: string;
    f1_friendly?: string;
    job_type?: string;
    work_mode?: string;
    posted_within?: string;
    matched?: string;
    selected?: string;
  }>;
}

export default async function HomePage({ searchParams }: HomePageProps) {
  const params = await searchParams;
  const currentPage = parseInt(params.page || "1", 10);
  const isMatched = params.matched === "true";
  const session = await auth();
  
  const [data, companies, locations, categories] = await Promise.all([
    isMatched 
      ? Promise.resolve({ items: [], total: 0, page: 1, page_size: 20 })
      : fetchJobs({ 
          page: currentPage,
          search: params.search,
          company: params.company,
          location: params.location,
          category: params.category,
          visa_sponsored: params.visa_sponsored,
          f1_friendly: params.f1_friendly,
          job_type: params.job_type,
          work_mode: params.work_mode,
          posted_within: params.posted_within,
        }),
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
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <header className="flex items-center justify-between">
        <div>
          <Link href="/" className="hover:opacity-80 transition-opacity">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                  InternNexus
                </h1>
            </Link>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Find your next internship
          </p>
        </div>
        <div className="flex items-center gap-4">
          <UserMenu user={session?.user} />
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
      />
    </div>
  );
}
