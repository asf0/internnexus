import { describe, expect, it } from 'vitest';
import { jobPostingEmploymentType, jobPostingValidThrough } from '@/lib/job-posting-schema';

describe('JobPosting JSON-LD helpers', () => {
  it('maps backend job types to schema.org employmentType enums', () => {
    expect(jobPostingEmploymentType('internship')).toBe('INTERN');
    expect(jobPostingEmploymentType('full_time')).toBe('FULL_TIME');
    expect(jobPostingEmploymentType('part_time')).toBe('PART_TIME');
  });

  it('is case-insensitive and falls back to OTHER for unknown values', () => {
    expect(jobPostingEmploymentType('FULL_TIME')).toBe('FULL_TIME');
    expect(jobPostingEmploymentType('contract')).toBe('OTHER');
    expect(jobPostingEmploymentType(null)).toBe('OTHER');
    expect(jobPostingEmploymentType(undefined)).toBe('OTHER');
  });

  it('derives validThrough 90 days after posting', () => {
    expect(jobPostingValidThrough('2026-01-01T00:00:00Z')).toBe('2026-04-01T00:00:00.000Z');
  });

  it('returns undefined for missing or invalid dates', () => {
    expect(jobPostingValidThrough(null)).toBeUndefined();
    expect(jobPostingValidThrough('not-a-date')).toBeUndefined();
  });
});
