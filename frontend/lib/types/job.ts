// Job-related types

export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  city: string | null;
  state: string | null;
  country: string | null;
  apply_url: string;
  description_text: string;
  visa_sponsored: boolean | null;
  f1_friendly: boolean | null;
  job_category: string | null;
  requires_sponsorship: boolean | null;
  requires_us_citizenship: boolean | null;
  application_closed: boolean | null;
  is_faang_plus: boolean | null;
  requires_advanced_degree: boolean | null;
  posted_at: string | null;
  is_active: boolean;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface JobFilters {
  page?: number;
  page_size?: number;
  search?: string;
  company?: string;
  location?: string;
  category?: string;
  visa_sponsored?: string;
  f1_friendly?: string;
  job_type?: string;
  work_mode?: string;
  posted_within?: string;
  match_ids?: string;
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
  error?: string;
}
