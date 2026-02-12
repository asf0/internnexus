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
