/**
 * Google's JobPosting `employmentType` accepts a fixed enum. The backend's
 * raw values (`internship`, `full_time`, ...) are not valid members, so they
 * are mapped here; unknown or missing values fall back to OTHER rather than
 * emitting an invalid literal.
 */
const EMPLOYMENT_TYPE_MAP: Record<string, string> = {
  internship: 'INTERN',
  full_time: 'FULL_TIME',
  part_time: 'PART_TIME',
};

/** How long a posting is treated as open after it was first seen. */
const JOB_POSTING_VALID_DAYS = 90;

export function jobPostingEmploymentType(jobType: string | null | undefined): string {
  if (!jobType) return 'OTHER';
  return EMPLOYMENT_TYPE_MAP[jobType.toLowerCase()] ?? 'OTHER';
}

export function jobPostingValidThrough(postedAt: string | null | undefined): string | undefined {
  if (!postedAt) return undefined;
  const posted = new Date(postedAt);
  if (Number.isNaN(posted.getTime())) return undefined;
  const validThrough = new Date(posted.getTime());
  validThrough.setDate(validThrough.getDate() + JOB_POSTING_VALID_DAYS);
  return validThrough.toISOString();
}
