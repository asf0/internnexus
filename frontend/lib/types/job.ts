// Job-related types

export interface Job {
  id: string;
  source: string;
  title: string;
  company: string;
  location: string;
  city: string | null;
  state: string | null;
  country: string | null;
  apply_url: string;
  description_text: string;
  job_category: string | null;
  job_type: string | null;
  work_mode: string | null;
  posted_at: string | null;
  is_active: boolean;
}

export interface JobFilters {
  page?: number;
  page_size?: number;
  search?: string;
  company?: string;
  location?: string;
  category?: string;
  job_type?: string;
  work_mode?: string;
  posted_within?: string;
  match_ids?: string;
}

export interface LocationItem {
  value: string;
  label: string;
  count: number;
  type: "country" | "state" | "city";
  country?: string;
  state?: string;
  children?: LocationItem[];
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface MatchResult {
  job_id: string;
  score: number;
  match_percentage: number;
  title: string;
  company: string;
  location: string;
}

export interface MatchResponse {
  matches: MatchResult[];
  total: number;
  session_id: string;
  page: number;
  page_size: number;
  total_pages: number;
  error?: string;
}

export interface MatchPageRequest {
  session_id: string;
  page?: number;
  page_size?: number;
  search?: string;
  company?: string;
  location?: string;
  category?: string;
  job_type?: string;
  work_mode?: string;
  posted_within?: string;
}
