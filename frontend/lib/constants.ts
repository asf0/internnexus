// Shared constants across the application

export const JOB_TYPE_LABEL_MAP: Record<string, string> = {
  "internship": "Internship",
  "full_time": "Full-time",
  "part_time": "Part-time",
};

export const WORK_MODE_LABEL_MAP: Record<string, string> = {
  "remote": "Remote",
  "hybrid": "Hybrid",
  "on_site": "On-site",
};

export const DEFAULT_PAGE_SIZE = 20;

export const LOCAL_STORAGE_KEYS = {
  MATCH_SCORES: "matchScores",
} as const;

export const SESSION_STORAGE_KEYS = {
  MATCH_SESSION: "match_session",
  PENDING_APPLY_URL: "pendingApplyUrl",
  PENDING_APPLY_JOB_ID: "pendingApplyJobId",
} as const;

export const DELETE_CONFIRM_TEXT = "DELETE";

export const SESSION_MAX_AGE_SECONDS = 24 * 60 * 60; // 24 hours
export const SESSION_UPDATE_AGE_SECONDS = 1 * 60 * 60; // 1 hour (sliding expiration)
