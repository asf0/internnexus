/**
 * Pagination and search for the public company directory.
 *
 * The catalogue has ~9k companies. Rendering every link in one response made
 * `/companies` a multi-hundred-KB HTML document with thousands of DOM nodes.
 * This keeps the server-side filter cheap and the response bounded.
 */

export const COMPANY_PAGE_SIZE = 200;

export interface CompanyDirectoryParams {
  readonly page?: string;
  readonly q?: string;
}

export interface CompanyDirectoryPage {
  readonly items: string[];
  readonly total: number;
  readonly page: number;
  readonly totalPages: number;
  readonly query: string;
}

export function buildCompanyDirectory(
  companies: readonly string[],
  params: CompanyDirectoryParams = {}
): CompanyDirectoryPage {
  const query = (params.q ?? '').trim();
  const normalized = query.toLowerCase();
  const filtered = normalized
    ? companies.filter((company) => company.toLowerCase().includes(normalized))
    : companies;

  const totalPages = Math.max(1, Math.ceil(filtered.length / COMPANY_PAGE_SIZE));
  const parsedPage = Number.parseInt(params.page ?? '1', 10);
  const page =
    Number.isInteger(parsedPage) && parsedPage > 0 ? Math.min(parsedPage, totalPages) : 1;
  const start = (page - 1) * COMPANY_PAGE_SIZE;

  return {
    items: filtered.slice(start, start + COMPANY_PAGE_SIZE),
    total: filtered.length,
    page,
    totalPages,
    query,
  };
}

/** Canonical-ish URL for a directory page, preserving the search query. */
export function companyDirectoryHref(page: number, query: string): string {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (page > 1) params.set('page', String(page));
  const suffix = params.toString();
  return suffix ? `/companies?${suffix}` : '/companies';
}
