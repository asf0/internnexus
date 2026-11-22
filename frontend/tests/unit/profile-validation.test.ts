import { describe, expect, it } from 'vitest';
import { userProfileSchema } from '@/lib/validation';

describe('userProfileSchema', () => {
  it('normalizes empty optional fields to null', () => {
    const result = userProfileSchema.parse({ name: '  ', linkedin_url: '', portfolio_url: '' });
    expect(result).toEqual(
      expect.objectContaining({ name: null, linkedin_url: null, portfolio_url: null })
    );
  });

  it.each([
    'javascript:alert(1)',
    'https://user:password@example.com',
    'ftp://example.com/profile',
  ])('rejects unsafe portfolio URL %s', (portfolio_url) => {
    expect(userProfileSchema.safeParse({ portfolio_url }).success).toBe(false);
  });

  it('requires a LinkedIn hostname for LinkedIn URLs', () => {
    expect(
      userProfileSchema.safeParse({ linkedin_url: 'https://example.com/in/person' }).success
    ).toBe(false);
    expect(
      userProfileSchema.safeParse({ linkedin_url: 'https://www.linkedin.com/in/person' }).success
    ).toBe(true);
  });
});
