import Link from 'next/link';
import type { JobSummary } from '@/lib/types';
import { companySlug, categorySlug } from '@/lib/hub-slugs';

interface RelatedJobsProps {
  readonly company: string;
  readonly category: string | null;
  readonly jobs: JobSummary[];
}

/**
 * Internal-link modules for the job detail page. Every job page is otherwise
 * an orphan (its only outbound links pointed back at the search homepage),
 * which starves crawl discovery and keeps pages in "Crawled - not indexed".
 * Same-company jobs first, then same-category ones.
 */
export default function RelatedJobs({ company, category, jobs }: RelatedJobsProps) {
  const companyJobs = jobs.filter((job) => job.company === company).slice(0, 5);
  const categoryJobs = jobs.filter((job) => job.company !== company).slice(0, 5);

  if (companyJobs.length === 0 && categoryJobs.length === 0) return null;

  return (
    <aside className="space-y-8 pt-4">
      {companyJobs.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-foreground text-lg font-semibold">More jobs at {company}</h2>
          <ul className="space-y-2">
            {companyJobs.map((job) => (
              <li key={job.id}>
                <Link
                  href={`/jobs/${job.id}`}
                  className="text-foreground-secondary hover:text-foreground text-sm underline-offset-4 hover:underline"
                >
                  {job.title}
                  <span className="text-foreground-muted"> — {job.location}</span>
                </Link>
              </li>
            ))}
          </ul>
          <Link
            href={`/companies/${companySlug(company)}`}
            className="text-accent inline-block text-sm font-medium underline-offset-4 hover:underline"
          >
            All {company} jobs →
          </Link>
        </section>
      )}

      {categoryJobs.length > 0 && category && (
        <section className="space-y-3">
          <h2 className="text-foreground text-lg font-semibold">Similar roles</h2>
          <ul className="space-y-2">
            {categoryJobs.map((job) => (
              <li key={job.id}>
                <Link
                  href={`/jobs/${job.id}`}
                  className="text-foreground-secondary hover:text-foreground text-sm underline-offset-4 hover:underline"
                >
                  {job.title}
                  <span className="text-foreground-muted"> — {job.company}</span>
                </Link>
              </li>
            ))}
          </ul>
          <Link
            href={`/categories/${categorySlug(category)}`}
            className="text-accent inline-block text-sm font-medium underline-offset-4 hover:underline"
          >
            Browse similar roles →
          </Link>
        </section>
      )}
    </aside>
  );
}
