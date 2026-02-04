export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  city?: string | null;
  state?: string | null;
  country?: string | null;
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
