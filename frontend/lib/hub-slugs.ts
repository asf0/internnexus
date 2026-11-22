/**
 * URL-safe slugs for hub pages. Company and category names come from the
 * backend and may contain any characters; slugs must be reversible enough to
 * resolve back to the canonical name via the cached facet lists.
 */

/** Characters that are unsafe or ambiguous in URLs get collapsed here. */
const SLUG_SEPARATOR = '-';

export function toHubSlug(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, SLUG_SEPARATOR)
    .replace(new RegExp(`^${SLUG_SEPARATOR}+|${SLUG_SEPARATOR}+$`, 'g'), '');
}

/**
 * Resolve a request slug back to the canonical name from the facet list.
 * Exact slug match wins; ties are resolved deterministically by name so the
 * same slug always serves the same company across requests.
 */
export function fromHubSlug(slug: string, names: string[]): string | null {
  const normalized = slug.toLowerCase();
  const matches = names.filter((name) => toHubSlug(name) === normalized);
  if (matches.length === 0) return null;
  // Default sort orders by UTF-16 code units: locale-independent and stable,
  // so the same slug always resolves to the same name across requests.
  matches.sort();
  return matches[0];
}

export function companySlug(company: string): string {
  return toHubSlug(company);
}

export function categorySlug(category: string): string {
  return toHubSlug(category);
}
