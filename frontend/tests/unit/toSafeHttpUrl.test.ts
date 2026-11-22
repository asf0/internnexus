import { describe, it, expect } from 'vitest';
import { toSafeHttpUrl } from '@/lib/utils';

describe('toSafeHttpUrl', () => {
  it('returns null for null, undefined, and non-string values', () => {
    expect(toSafeHttpUrl(null)).toBeNull();
    expect(toSafeHttpUrl(undefined)).toBeNull();
    expect(toSafeHttpUrl('')).toBeNull();
  });

  it('normalizes and returns valid http/https URLs', () => {
    expect(toSafeHttpUrl('https://example.com/apply')).toBe('https://example.com/apply');
    expect(toSafeHttpUrl('  http://example.com/apply  ')).toBe('http://example.com/apply');
  });

  it('rejects non-http protocols', () => {
    expect(toSafeHttpUrl('javascript:alert(1)')).toBeNull();
    expect(toSafeHttpUrl('ftp://example.com/file')).toBeNull();
    expect(toSafeHttpUrl('file:///etc/passwd')).toBeNull();
    expect(toSafeHttpUrl('mailto:test@example.com')).toBeNull();
  });

  it('rejects malformed URLs', () => {
    expect(toSafeHttpUrl('not a url')).toBeNull();
    expect(toSafeHttpUrl('https://')).toBeNull();
  });
});
