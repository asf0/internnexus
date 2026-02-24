export const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL!;

const parseBooleanFlag = (value: string | undefined, defaultValue: boolean): boolean => {
  if (value === undefined) return defaultValue;
  return value.toLowerCase() === "true";
};

export const SHOW_JOB_COUNT = parseBooleanFlag(process.env.NEXT_PUBLIC_SHOW_JOB_COUNT, true);
