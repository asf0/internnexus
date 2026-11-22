import { describe, expect, it } from 'vitest';
import { toHubSlug, fromHubSlug, companySlug, categorySlug } from '@/lib/hub-slugs';

describe('hub slugs', () => {
  it('slugifies company and category names', () => {
    expect(companySlug('Acme Corp')).toBe('acme-corp');
    expect(categorySlug('software_engineering')).toBe('software-engineering');
    expect(toHubSlug('  Ben & Josh Co.  ')).toBe('ben-josh-co');
  });

  it('resolves a slug back to the canonical name', () => {
    const names = ['Acme Corp', 'Ben'];
    expect(fromHubSlug('acme-corp', names)).toBe('Acme Corp');
    expect(fromHubSlug('ben', names)).toBe('Ben');
  });

  it('returns null for unknown slugs', () => {
    expect(fromHubSlug('nope', ['Acme Corp'])).toBeNull();
    expect(fromHubSlug('', ['Acme Corp'])).toBeNull();
  });

  it('resolves slug collisions deterministically', () => {
    // "A.B" and "A B" slugify identically; the code-unit sort tie-break keeps
    // the same name serving the same slug across requests.
    const resolved = fromHubSlug('a-b', ['A B', 'A.B', 'a b']);
    expect(resolved).toBe('A B');
  });
});
