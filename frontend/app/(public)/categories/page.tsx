import type { Metadata } from 'next';
import Link from 'next/link';
import { fetchCategories } from '@/lib/api';
import { BASE_URL } from '@/lib/config';
import { SITE_NAME, siteOpenGraphImage } from '@/lib/seo';
import { categorySlug } from '@/lib/hub-slugs';
import { formatCategoryLabel } from '@/lib/utils';

export const metadata: Metadata = {
  title: 'Browse jobs by category',
  description:
    'Internships and entry-level jobs grouped by category — engineering, design, data, and more.',
  alternates: {
    canonical: `${BASE_URL}/categories`,
  },
  openGraph: {
    title: `Browse jobs by category | ${SITE_NAME}`,
    description: 'Internships and entry-level jobs grouped by category.',
    url: `${BASE_URL}/categories`,
    images: siteOpenGraphImage(),
  },
};

// Rendered on demand: prerendering here would bake an empty directory into
// the build, which runs without a backend. The facet fetch below still hits
// its one-hour Data Cache, so the per-request cost stays trivial.
export const dynamic = 'force-dynamic';

export default async function CategoriesPage() {
  const categories = await fetchCategories();

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-foreground text-3xl font-semibold">Categories</h1>
        <p className="text-foreground-secondary text-sm">
          {categories.length > 0
            ? `${categories.length} job categories with current openings.`
            : 'Category listings are temporarily unavailable. Please check back soon.'}
        </p>
      </header>

      <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {categories.map((category) => (
          <li key={category}>
            <Link
              href={`/categories/${categorySlug(category)}`}
              className="border-border bg-surface hover:bg-surface-subtle block rounded-lg border px-4 py-3 text-sm font-medium transition-colors"
            >
              {formatCategoryLabel(category)}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
