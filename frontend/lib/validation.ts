import { z } from 'zod';

const normalizeOptionalString = (value: unknown): unknown => {
  if (typeof value !== 'string') return value;
  const trimmed = value.trim();
  return trimmed === '' ? null : trimmed;
};

const optionalText = (schema: z.ZodString) =>
  z.preprocess(normalizeOptionalString, schema.nullable().optional());

const safeHttpUrl = z
  .string()
  .trim()
  .max(2048, 'URL must be less than 2048 characters')
  .refine((value) => {
    try {
      const url = new URL(value);
      return (
        (url.protocol === 'http:' || url.protocol === 'https:') && !url.username && !url.password
      );
    } catch {
      return false;
    }
  }, 'Must be a valid HTTP(S) URL without embedded credentials');

export const userProfileSchema = z.object({
  name: optionalText(
    z.string().min(2, 'Name must be at least 2 characters').max(100, 'Name is too long')
  ),
  bio: optionalText(z.string().max(500, 'Bio must be less than 500 characters')),
  phone: optionalText(z.string().regex(/^\+?[\d\s\-().]+$/, 'Invalid phone number format')),
  location: optionalText(z.string().max(100, 'Location must be less than 100 characters')),
  job_title: optionalText(z.string().max(100, 'Job title must be less than 100 characters')),
  company: optionalText(z.string().max(100, 'Company must be less than 100 characters')),
  industry: optionalText(z.string().max(50, 'Industry must be less than 50 characters')),
  skills: z.array(z.string().min(1).max(50)).max(20, 'Maximum 20 skills allowed').default([]),
  linkedin_url: z.preprocess(
    normalizeOptionalString,
    safeHttpUrl
      .refine((value) => {
        const hostname = new URL(value).hostname.toLowerCase();
        return hostname === 'linkedin.com' || hostname.endsWith('.linkedin.com');
      }, 'Must use a LinkedIn hostname')
      .nullable()
      .optional()
  ),
  portfolio_url: z.preprocess(normalizeOptionalString, safeHttpUrl.nullable().optional()),
  preferred_locations: z
    .array(z.string().min(1).max(100))
    .max(10, 'Maximum 10 preferred locations')
    .default([]),
});

export type UserProfileFormData = z.infer<typeof userProfileSchema>;

export const passwordChangeSchema = z
  .object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[A-Z]/, 'Must contain at least one uppercase letter')
      .regex(/[a-z]/, 'Must contain at least one lowercase letter')
      .regex(/\d/, 'Must contain at least one number')
      .regex(/[^A-Za-z\d]/, 'Must contain at least one special character'),
    confirm_password: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  });

export type PasswordChangeFormData = z.infer<typeof passwordChangeSchema>;

export const registrationSchema = z
  .object({
    name: z
      .string()
      .min(2, 'Name must be at least 2 characters')
      .max(100, 'Name must be less than 100 characters')
      .optional(),
    email: z.email('Invalid email address').min(1, 'Email is required'),
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[A-Z]/, 'Must contain at least one uppercase letter')
      .regex(/[a-z]/, 'Must contain at least one lowercase letter')
      .regex(/\d/, 'Must contain at least one number')
      .regex(/[^A-Za-z\d]/, 'Must contain at least one special character'),
    confirm_password: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  });

export type RegistrationFormData = z.infer<typeof registrationSchema>;

export const loginSchema = z.object({
  email: z.email('Invalid email address').min(1, 'Email is required'),
  password: z.string().min(1, 'Password is required'),
});

export type LoginFormData = z.infer<typeof loginSchema>;
