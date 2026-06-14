import { z } from 'zod';
import type { LocationItem } from './types/job';

// ============================================================================
// Job schemas
// ============================================================================

export const JobSchema = z.object({
  id: z.string(),
  source: z.string(),
  title: z.string(),
  company: z.string(),
  location: z.string(),
  city: z.string().nullable(),
  state: z.string().nullable(),
  country: z.string().nullable(),
  apply_url: z.string(),
  description_text: z.string(),
  job_category: z.string().nullable(),
  job_type: z.string().nullable(),
  work_mode: z.string().nullable(),
  posted_at: z.string().nullable(),
  is_active: z.boolean(),
});

export const JobListResponseSchema = z.object({
  items: z.array(JobSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
});

export const LocationItemSchema: z.ZodType<LocationItem> = z.lazy(() =>
  z.object({
    value: z.string(),
    label: z.string(),
    count: z.number(),
    type: z.enum(['country', 'state', 'city']),
    country: z.string().optional(),
    state: z.string().optional(),
    children: z.array(LocationItemSchema).optional(),
  })
);

export const FacetItemSchema = z.object({
  value: z.string(),
  label: z.string(),
  count: z.number(),
});

export const MatchResultSchema = z.object({
  job_id: z.string(),
  score: z.number(),
  match_percentage: z.number(),
  title: z.string(),
  company: z.string(),
  location: z.string(),
  apply_url: z.string(),
  description_text: z.string(),
  city: z.string().nullable().optional(),
  state: z.string().nullable().optional(),
  country: z.string().nullable().optional(),
  job_category: z.string().nullable().optional(),
  job_type: z.string().nullable().optional(),
  work_mode: z.string().nullable().optional(),
  posted_at: z.string().nullable().optional(),
  score_breakdown: z
    .object({
      semantic: z.number(),
      skill_title: z.number(),
      work_mode: z.number(),
      recency: z.number(),
      final: z.number(),
    })
    .optional(),
});

export const MatchResponseSchema = z.object({
  matches: z.array(MatchResultSchema),
  total: z.number(),
  session_id: z.string(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
  reused_from_cache: z.boolean().optional(),
  error: z.string().optional(),
});

export const MatchFacetsResponseSchema = z.object({
  companies: z.array(FacetItemSchema),
  categories: z.array(FacetItemSchema),
  job_types: z.array(FacetItemSchema),
  work_modes: z.array(FacetItemSchema),
  locations: z.array(LocationItemSchema),
  total_matches: z.number(),
});

// ============================================================================
// User schemas
// ============================================================================

export const UserProfileSchema = z.object({
  id: z.string(),
  email: z.string(),
  name: z.string().nullable(),
  image: z.string().nullable(),
  created_at: z.string(),
  bio: z.string().nullable(),
  phone: z.string().nullable(),
  location: z.string().nullable(),
  job_title: z.string().nullable(),
  company: z.string().nullable(),
  industry: z.string().nullable(),
  skills: z.array(z.string()),
  linkedin_url: z.string().nullable(),
  portfolio_url: z.string().nullable(),
  preferred_locations: z.array(z.string()),
  has_password: z.boolean(),
});

export const UserResumeSchema = z.object({
  id: z.string(),
  file_name: z.string(),
  file_hash: z.string(),
  content_hash: z.string().nullable(),
  status: z.string(),
  has_embedding: z.boolean(),
  embedding_model: z.string().nullable(),
  embedding_dim: z.number().nullable(),
  last_embedded_at: z.string().nullable(),
  embedding_error: z.string().nullable(),
  uploaded_at: z.string(),
  updated_at: z.string(),
});

export const NotificationItemSchema = z.object({
  id: z.string(),
  type: z.string(),
  payload: z.record(z.string(), z.unknown()),
  is_read: z.boolean(),
  created_at: z.string(),
  read_at: z.string().nullable(),
});

export const SavedJobRecordSchema = z.object({
  id: z.string(),
  job_id: z.string(),
  created_at: z.string(),
  job: JobSchema,
});

export const UnreadCountResponseSchema = z.object({
  unread_count: z.number(),
});

// ============================================================================
// Auth schemas
// ============================================================================

export const AuthResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.string(),
  user: z.object({
    id: z.string(),
    email: z.string(),
    name: z.string().nullable(),
    image: z.string().nullable(),
  }),
});

// ============================================================================
// Admin schemas
// ============================================================================

export const AdminJobSchema = z.object({
  id: z.string(),
  source: z.string(),
  title: z.string(),
  company: z.string(),
  location: z.string(),
  city: z.string().nullable(),
  state: z.string().nullable(),
  country: z.string().nullable(),
  apply_url: z.string(),
  description_text: z.string(),
  job_category: z.string().nullable(),
  job_type: z.string().nullable(),
  work_mode: z.string().nullable(),
  posted_at: z.string().nullable(),
  is_active: z.boolean(),
  click_count: z.number(),
  created_at: z.string().nullable(),
});

export const AdminUserSchema = z.object({
  id: z.string(),
  email: z.string(),
  name: z.string().nullable(),
  is_active: z.boolean(),
  created_at: z.string(),
  has_password: z.boolean(),
  admin_role: z.string().nullable(),
  provider: z.string().nullable(),
  notes: z.string().nullable(),
});

export function PaginatedResponseSchema<T>(itemSchema: z.ZodSchema<T>) {
  return z.object({
    items: z.array(itemSchema),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
    total_pages: z.number().optional(),
  });
}

export const UserClickSchema = z.object({
  id: z.string(),
  job_id: z.string(),
  job_title: z.string(),
  company: z.string(),
  apply_url: z.string(),
  clicked_at: z.string(),
  utm_source: z.string(),
  utm_medium: z.string().nullable(),
  utm_campaign: z.string().nullable(),
});

export const ClicksByUserSchema = z.object({
  user_id: z.string().nullable(),
  email: z.string().nullable(),
  name: z.string().nullable(),
  click_count: z.number(),
});

export const HourlyClicksSchema = z.object({
  hour: z.number(),
  clicks: z.number(),
});

export const TopJobByClicksSchema = z.object({
  job_id: z.string(),
  title: z.string(),
  company: z.string(),
  apply_url: z.string().nullable(),
  click_count: z.number(),
});

export const DayClickStatsSchema = z.object({
  date: z.string(),
  total_clicks: z.number(),
  unique_jobs: z.number(),
  unique_users: z.number(),
  anonymous_clicks: z.number(),
  clicks_by_hour: z.array(HourlyClicksSchema),
  top_jobs: z.array(TopJobByClicksSchema),
});

export const BulkActionResponseSchema = z.object({
  affected: z.number(),
});

export const CreateJobResponseSchema = AdminJobSchema;

export const CreateUserResponseSchema = AdminUserSchema;

export const ResetPasswordResponseSchema = z.object({
  message: z.string(),
});

export const CurrentAdminInfoSchema = z.object({
  id: z.string(),
  role: z.enum(['admin', 'super_admin']),
});

// ============================================================================
// Job click schema
// ============================================================================

export const ClickResponseSchema = z.object({
  apply_url: z.string(),
  job_id: z.string(),
});

// ============================================================================
// Admin dashboard / stats schemas
// ============================================================================

export const JobStatsSchema = z.object({
  total_jobs: z.number(),
  active_jobs: z.number(),
  total_companies: z.number(),
  jobs_by_category: z.record(z.string(), z.number()),
});

export const ClickStatsSchema = z.object({
  total_clicks: z.number(),
  clicks_today: z.number(),
  clicks_this_week: z.number(),
  clicks_this_month: z.number(),
  authenticated_clicks_total: z.number(),
  anonymous_clicks_total: z.number(),
  unique_users_total: z.number(),
  unique_jobs_total: z.number(),
  clicks_last_24h: z.number(),
  avg_clicks_per_day_30d: z.number(),
  top_sources: z.array(
    z.object({
      value: z.string(),
      click_count: z.number(),
    })
  ),
  top_mediums: z.array(
    z.object({
      value: z.string(),
      click_count: z.number(),
    })
  ),
  top_campaigns: z.array(
    z.object({
      value: z.string(),
      click_count: z.number(),
    })
  ),
  clicks_by_hour_today: z.array(
    z.object({
      hour: z.number(),
      clicks: z.number(),
    })
  ),
  daily_breakdown_14d: z.array(
    z.object({
      date: z.string(),
      clicks: z.number(),
      unique_users: z.number(),
    })
  ),
  top_jobs: z.array(
    z.object({
      job_id: z.string(),
      title: z.string(),
      company: z.string(),
      click_count: z.number(),
    })
  ),
});

export const ClickByDaySchema = z.object({
  date: z.string(),
  clicks: z.number(),
  unique_users: z.number().optional(),
  unique_jobs: z.number().optional(),
});

export const ClickByDayArraySchema = z.array(ClickByDaySchema);

export const JobClickSchema = z.object({
  id: z.string(),
  job_id: z.string(),
  job_title: z.string(),
  company: z.string(),
  user_id: z.string().nullable(),
  user_email: z.string().nullable(),
  user_name: z.string().nullable(),
  clicked_at: z.string(),
  utm_source: z.string(),
  utm_medium: z.string().nullable(),
  utm_campaign: z.string().nullable(),
  apply_url: z.string().nullable(),
});

export const ClicksListResponseSchema = z.object({
  items: z.array(JobClickSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

export const PipelineStatsSchema = z.object({
  total_runs: z.number(),
  completed: z.number(),
  failed: z.number(),
  running: z.number(),
  last_success: z.string().nullable(),
  last_failure: z.string().nullable(),
});

export const PipelineRunSchema = z.object({
  id: z.string(),
  status: z.string(),
  step_completed: z.string().nullable(),
  error_message: z.string().nullable(),
  error_step: z.string().nullable(),
  started_at: z.string(),
  completed_at: z.string().nullable(),
  results: z.string().nullable(),
});

export const PipelineRunsListResponseSchema = z.object({
  items: z.array(PipelineRunSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});
