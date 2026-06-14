export function getMatchColor(percentage: number): string {
  if (percentage >= 80) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
  if (percentage >= 60) return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
  if (percentage >= 40) return 'bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200';
  return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
}

/**
 * Formats a category slug into a readable label.
 * e.g., "software_engineering" → "Software Engineering"
 */
export function formatCategoryLabel(category: string | null | undefined): string {
  if (!category) return '';
  return category
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function parseApiError(error: unknown): string {
  if (!error || typeof error !== 'object') {
    return 'An error occurred';
  }

  const detail = (error as { detail?: { message?: string } | string }).detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return detail.message || 'An error occurred';
  }

  const message = (error as { message?: string }).message;
  if (typeof message === 'string') return message;

  return 'An error occurred';
}

export function generateJobSlug(title: string, company: string, id: string): string {
  const titleSlug = title
    .toLowerCase()
    .replaceAll(/[^a-z0-9\s-]/g, '')
    .replaceAll(/\s+/g, '-')
    .replaceAll(/-+/g, '-')
    .replaceAll(/(^-)|(-$)/g, '')
    .slice(0, 50);

  const companySlug = company
    .toLowerCase()
    .replaceAll(/[^a-z0-9\s-]/g, '')
    .replaceAll(/\s+/g, '-')
    .replaceAll(/-+/g, '-')
    .replaceAll(/(^-)|(-$)/g, '')
    .slice(0, 30);

  const idSuffix = id.slice(0, 8);

  return `${titleSlug}-at-${companySlug}-${idSuffix}`;
}

export function findJobBySlug<T extends { id: string; title: string; company: string }>(
  jobs: T[],
  slug: string
): T | undefined {
  const idSuffix = slug.slice(-8);
  return jobs.find((job) => job.id.startsWith(idSuffix));
}

export function toSafeHttpUrl(rawUrl: string | null | undefined): string | null {
  if (typeof rawUrl !== 'string') return null;

  const trimmed = rawUrl.trim();
  if (!trimmed) return null;

  try {
    const url = new URL(trimmed);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      return null;
    }
    return url.toString();
  } catch {
    return null;
  }
}
