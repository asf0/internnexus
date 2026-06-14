export interface AdminJob {
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
  click_count: number;
  created_at: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  name: string | null;
  is_active: boolean;
  created_at: string;
  has_password: boolean;
  admin_role: string | null;
  provider: string | null;
  notes: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages?: number;
}

export interface JobsListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  company?: string;
  category?: string;
  isActive?: boolean;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface UsersListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  isAdmin?: boolean;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface UserClick {
  id: string;
  job_id: string;
  job_title: string;
  company: string;
  apply_url: string;
  clicked_at: string;
  utm_source: string;
  utm_medium: string | null;
  utm_campaign: string | null;
}

export interface CreateJobRequest {
  title: string;
  company: string;
  location: string;
  apply_url: string;
  description_text: string;
  job_category?: string;
  job_type?: string;
  work_mode?: string;
  posted_at?: string;
}

export interface ClicksByUser {
  user_id: string | null;
  email: string | null;
  name: string | null;
  click_count: number;
}

export interface HourlyClicks {
  hour: number;
  clicks: number;
}

export interface TopJobByClicks {
  job_id: string;
  title: string;
  company: string;
  apply_url: string | null;
  click_count: number;
}

export interface DayClickStats {
  date: string;
  total_clicks: number;
  unique_jobs: number;
  unique_users: number;
  anonymous_clicks: number;
  clicks_by_hour: HourlyClicks[];
  top_jobs: TopJobByClicks[];
}
