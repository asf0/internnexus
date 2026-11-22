export const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

const baseUrl = process.env.NEXT_PUBLIC_BASE_URL;
if (!baseUrl) {
  throw new Error('NEXT_PUBLIC_BASE_URL environment variable is required');
}
export const BASE_URL = baseUrl;

const parseBooleanFlag = (value: string | undefined, defaultValue: boolean): boolean => {
  if (value === undefined) return defaultValue;
  return value.toLowerCase() === 'true';
};

export const SHOW_JOB_COUNT = parseBooleanFlag(process.env.NEXT_PUBLIC_SHOW_JOB_COUNT, true);

export const ENABLE_CREDENTIAL_AUTH = parseBooleanFlag(
  process.env.NEXT_PUBLIC_ENABLE_CREDENTIAL_AUTH,
  true
);
