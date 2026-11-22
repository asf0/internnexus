import { describe, expect, it } from 'vitest';
import {
  buildCompanyDirectory,
  companyDirectoryHref,
  COMPANY_PAGE_SIZE,
} from '@/lib/company-directory';

function companies(count: number): string[] {
  return Array.from({ length: count }, (_, index) => `Company ${String(index).padStart(4, '0')}`);
}

describe('buildCompanyDirectory', () => {
  it('returns every company on one page when under the page size', () => {
    const all = companies(10);
    const result = buildCompanyDirectory(all);

    expect(result.items).toEqual(all);
    expect(result.total).toBe(10);
    expect(result.page).toBe(1);
    expect(result.totalPages).toBe(1);
    expect(result.query).toBe('');
  });

  it('paginates a catalogue larger than the page size', () => {
    const all = companies(COMPANY_PAGE_SIZE * 2 + 50);
    const first = buildCompanyDirectory(all, { page: '1' });
    const second = buildCompanyDirectory(all, { page: '2' });
    const third = buildCompanyDirectory(all, { page: '3' });

    expect(first.items).toHaveLength(COMPANY_PAGE_SIZE);
    expect(second.items).toHaveLength(COMPANY_PAGE_SIZE);
    expect(third.items).toHaveLength(50);
    expect(first.totalPages).toBe(3);
    expect(first.items[0]).toBe(all[0]);
    expect(third.items[0]).toBe(all[COMPANY_PAGE_SIZE * 2]);
  });

  it('clamps an out-of-range page to the last page', () => {
    const result = buildCompanyDirectory(companies(COMPANY_PAGE_SIZE + 1), { page: '99' });

    expect(result.page).toBe(2);
    expect(result.items).toHaveLength(1);
  });

  it('falls back to page 1 for malformed page values', () => {
    expect(buildCompanyDirectory(companies(5), { page: 'nope' }).page).toBe(1);
    expect(buildCompanyDirectory(companies(5), { page: '0' }).page).toBe(1);
    expect(buildCompanyDirectory(companies(5), { page: '-3' }).page).toBe(1);
  });

  it('filters case-insensitively and keeps the original query text', () => {
    const all = ['Acme Corp', 'Beta Labs', 'acme robotics'];
    const result = buildCompanyDirectory(all, { q: '  ACME ' });

    expect(result.query).toBe('ACME');
    expect(result.total).toBe(2);
    expect(result.items).toEqual(['Acme Corp', 'acme robotics']);
  });

  it('returns an empty page when nothing matches', () => {
    const result = buildCompanyDirectory(['Acme'], { q: 'zzz' });

    expect(result.items).toEqual([]);
    expect(result.total).toBe(0);
    expect(result.totalPages).toBe(1);
    expect(result.page).toBe(1);
  });
});

describe('companyDirectoryHref', () => {
  it('uses the bare directory URL for the first page', () => {
    expect(companyDirectoryHref(1, '')).toBe('/companies');
  });

  it('adds only the page when there is no query', () => {
    expect(companyDirectoryHref(2, '')).toBe('/companies?page=2');
  });

  it('preserves the search query across pages', () => {
    expect(companyDirectoryHref(1, 'Acme')).toBe('/companies?q=Acme');
    expect(companyDirectoryHref(3, 'Acme')).toBe('/companies?q=Acme&page=3');
  });

  it('encodes query values', () => {
    expect(companyDirectoryHref(2, 'Acme & Sons')).toBe('/companies?q=Acme+%26+Sons&page=2');
  });
});
