import { describe, expect, it } from 'vitest';
import { hasActiveHomeFilters, homeMetadata } from '@/lib/seo';

const BASE_URL = 'https://example.com';

describe('homepage indexability', () => {
  it('treats the clean homepage as unfiltered', () => {
    expect(hasActiveHomeFilters({})).toBe(false);
    expect(hasActiveHomeFilters({ page: '1' })).toBe(false);
    expect(hasActiveHomeFilters({ auth: 'required' })).toBe(false);
    expect(hasActiveHomeFilters({ callbackUrl: '/settings' })).toBe(false);
  });

  it('detects every filter parameter', () => {
    for (const key of [
      'search',
      'company',
      'location',
      'category',
      'job_type',
      'work_mode',
      'posted_within',
      'saved_only',
      'matched',
    ]) {
      expect(hasActiveHomeFilters({ [key]: 'x' })).toBe(true);
    }
  });

  it('detects pages beyond the first', () => {
    expect(hasActiveHomeFilters({ page: '2' })).toBe(true);
    expect(hasActiveHomeFilters({ page: 'abc' })).toBe(false);
  });

  it('canonicalises the clean homepage and leaves it indexable', () => {
    const metadata = homeMetadata({}, BASE_URL);
    expect(metadata.alternates?.canonical).toBe(BASE_URL);
    expect(metadata.robots).toBeUndefined();
  });

  it('canonicalises filtered views to the clean homepage and noindexes them', () => {
    const metadata = homeMetadata({ company: 'google', page: '3' }, BASE_URL);
    expect(metadata.alternates?.canonical).toBe(BASE_URL);
    expect(metadata.robots).toEqual({ index: false, follow: true });
  });
});
