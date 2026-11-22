import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { fetchCategories, fetchJobs } from '@/lib/api';
import { hubMetadata } from '@/lib/seo';
import { categorySlug, fromHubSlug } from '@/lib/hub-slugs';
import { formatCategoryLabel } from '@/lib/utils';

interface CategoryHubPageProps {
  params: Promise<{ category: string }>;
  searchParams: Promise<{ page?: string }>;
}

const JOBS_PER_PAGE = 20;

export async function generateMetadata({ params }: CategoryHubPageProps): Promise<Metadata> {
  const { category: slug } = await params;
  const categories = await fetchCategories();
  const category = fromHubSlug(slug, categories);
  if (!category) {
    return { title: 'Category not found' };
  }

  const label = formatCategoryLabel(category);

  return hubMetadata(
    `/categories/${categorySlug(category)}`,
    1,
    `${label} internships & entry-level jobs`,
    `Current ${label.toLowerCase()} internships and entry-level openings across all companies on InternNexus.`
  );
}

export default async function CategoryHubPage({ params, searchParams }: CategoryHubPageProps) {
  const { category: slug } = await params;
  const { page: pageParam } = await searchParams;
  const parsedPage = Number.parseInt(pageParam || '1', 10);
  const page = Number.isInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  const categories = await fetchCategories();
  const category = fromHubSlug(slug, categories);
  if (!category) {
    notFound();
  }

  const label = formatCategoryLabel(category);
  const data = await fetchJobs({ category, page, page_size: JOBS_PER_PAGE });
  const totalPages = Math.max(1, Math.ceil(data.total / JOBS_PER_PAGE));

  return (
    <div className="space-y-6">
      <nav aria-label="Breadcrumb" className="text-sm">
        <ol className="flex flex-wrap items-center gap-1">
          <li>
            <Link
              href="/"
              className="text-foreground-secondary hover:text-foreground underline-offset-4 hover:underline"
            >
              Jobs
            </Link>
          </li>
          <li aria-hidden="true" className="text-foreground-muted">
            /
          </li>
          <li>
            <Link
              href="/categories"
              className="text-foreground-secondary hover:text-foreground underline-offset-4 hover:underline"
            >
              Categories
            </Link>
          </li>
        </ol>
      </nav>

      <header className="space-y-2">
        <h1 className="text-foreground text-3xl font-semibold">{label} jobs</h1>
        <p className="text-foreground-secondary text-sm">
          {data.total} current {data.total === 1 ? 'opening' : 'openings'}
        </p>
      </header>

      <ul className="space-y-3">
        {data.items.map((job) => (
          <li key={job.id}>
            <Link
              href={`/jobs/${job.id}`}
              className="border-border bg-surface hover:bg-surface-subtle block rounded-lg border px-4 py-3 transition-colors"
            >
              <p className="text-foreground font-medium">{job.title}</p>
              <p className="text-foreground-muted text-sm">
                {job.company} — {job.location}
              </p>
            </Link>
          </li>
        ))}
      </ul>

      {totalPages > 1 && (
        <nav aria-label="Pagination" className="flex items-center gap-4">
          {page > 1 && (
            <Link
              href={`/categories/${slug}?page=${page - 1}`}
              className="text-foreground-secondary hover:text-foreground text-sm underline-offset-4 hover:underline"
            >
              ← Previous
            </Link>
          )}
          <span className="text-foreground-muted text-sm">
            Page {page} of {totalPages}
          </span>
          {page < totalPages && (
            <Link
              href={`/categories/${slug}?page=${page + 1}`}
              className="text-foreground-secondary hover:text-foreground text-sm underline-offset-4 hover:underline"
            >
              Next →
            </Link>
          )}
        </nav>
      )}
    </div>
  );
}
