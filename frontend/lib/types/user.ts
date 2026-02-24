// User-related types

export interface UserProfile {
  id: string;
  email: string;
  name: string | null;
  image: string | null;
  created_at: string;
  bio: string | null;
  phone: string | null;
  location: string | null;
  job_title: string | null;
  company: string | null;
  industry: string | null;
  skills: string[];
  linkedin_url: string | null;
  portfolio_url: string | null;
  preferred_locations: string[];
  has_password: boolean;
}

export interface UpdateUserData {
  name?: string | null;
  bio?: string | null;
  phone?: string | null;
  location?: string | null;
  job_title?: string | null;
  company?: string | null;
  industry?: string | null;
  skills?: string[];
  linkedin_url?: string | null;
  portfolio_url?: string | null;
  preferred_locations?: string[];
}

export interface UserResume {
  id: string;
  file_name: string;
  file_hash: string;
  content_hash: string | null;
  status: string;
  has_embedding: boolean;
  embedding_model: string | null;
  embedding_dim: number | null;
  last_embedded_at: string | null;
  embedding_error: string | null;
  uploaded_at: string;
  updated_at: string;
}

export interface NotificationItem {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
}

export interface SavedJobRecord {
  id: string;
  job_id: string;
  created_at: string;
  job: {
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
  };
}
