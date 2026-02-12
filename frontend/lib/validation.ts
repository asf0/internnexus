import { z } from "zod";

/**
 * User profile validation schema
 */
export const userProfileSchema = z.object({
  name: z
    .string()
    .min(2, "Name must be at least 2 characters")
    .max(100, "Name must be less than 100 characters")
    .optional()
    .or(z.literal("")),
  bio: z
    .string()
    .max(500, "Bio must be less than 500 characters")
    .optional()
    .or(z.literal("")),
  phone: z
    .string()
    .regex(
      /^$|^\+?[\d\s\-\(\)\.]+$/,
      "Invalid phone number format"
    )
    .optional()
    .or(z.literal("")),
  location: z
    .string()
    .max(100, "Location must be less than 100 characters")
    .optional()
    .or(z.literal("")),
  job_title: z
    .string()
    .max(100, "Job title must be less than 100 characters")
    .optional()
    .or(z.literal("")),
  company: z
    .string()
    .max(100, "Company must be less than 100 characters")
    .optional()
    .or(z.literal("")),
  industry: z
    .string()
    .max(50, "Industry must be less than 50 characters")
    .optional()
    .or(z.literal("")),
  skills: z
    .array(z.string().min(1).max(50))
    .max(20, "Maximum 20 skills allowed")
    .default([]),
  linkedin_url: z
    .string()
    .regex(
      /^$|^https?:\/\/(www\.)?linkedin\.com\/.*$/,
      "Must be a valid LinkedIn URL"
    )
    .optional()
    .or(z.literal("")),
  portfolio_url: z
    .string()
    .regex(
      /^$|^https?:\/\/.+$/,
      "Must be a valid URL (http:// or https://)"
    )
    .optional()
    .or(z.literal("")),
  preferred_locations: z
    .array(z.string().min(1).max(100))
    .max(10, "Maximum 10 preferred locations")
    .default([]),
});

export type UserProfileFormData = z.infer<typeof userProfileSchema>;

/**
 * Password change validation schema
 */
export const passwordChangeSchema = z
  .object({
    current_password: z
      .string()
      .min(1, "Current password is required"),
    new_password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Must contain at least one uppercase letter")
      .regex(/[a-z]/, "Must contain at least one lowercase letter")
      .regex(/[0-9]/, "Must contain at least one number")
      .regex(
        /[^A-Za-z0-9]/,
        "Must contain at least one special character"
      ),
    confirm_password: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

export type PasswordChangeFormData = z.infer<typeof passwordChangeSchema>;

/**
 * Registration validation schema
 */
export const registrationSchema = z
  .object({
    name: z
      .string()
      .min(2, "Name must be at least 2 characters")
      .max(100, "Name must be less than 100 characters")
      .optional(),
    email: z
      .string()
      .min(1, "Email is required")
      .email("Invalid email address"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Must contain at least one uppercase letter")
      .regex(/[a-z]/, "Must contain at least one lowercase letter")
      .regex(/[0-9]/, "Must contain at least one number")
      .regex(
        /[^A-Za-z0-9]/,
        "Must contain at least one special character"
      ),
    confirm_password: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

export type RegistrationFormData = z.infer<typeof registrationSchema>;

/**
 * Login validation schema
 */
export const loginSchema = z.object({
  email: z
    .string()
    .min(1, "Email is required")
    .email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
});

export type LoginFormData = z.infer<typeof loginSchema>;

/**
 * Job filters validation schema
 */
export const jobFiltersSchema = z.object({
  search: z.string().optional(),
  company: z.array(z.string()).default([]),
  location: z.array(z.string()).default([]),
  category: z.array(z.string()).default([]),
  visa_sponsored: z.boolean().optional(),
  f1_friendly: z.boolean().optional(),
  job_type: z.string().optional(),
  work_mode: z.string().optional(),
  posted_within: z.string().optional(),
});

export type JobFiltersFormData = z.infer<typeof jobFiltersSchema>;

/**
 * Resume upload validation schema
 */
export const resumeUploadSchema = z.object({
  file: z
    .instanceof(File)
    .refine((file) => file.size > 0, "File is required")
    .refine(
      (file) => file.size <= 5 * 1024 * 1024,
      "File size must be less than 5MB"
    )
    .refine(
      (file) =>
        ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"].includes(file.type),
      "Only PDF and Word documents are allowed"
    ),
});

export type ResumeUploadFormData = z.infer<typeof resumeUploadSchema>;

/**
 * Password set validation schema (for OAuth users setting password)
 */
export const passwordSetSchema = z
  .object({
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Must contain at least one uppercase letter")
      .regex(/[a-z]/, "Must contain at least one lowercase letter")
      .regex(/[0-9]/, "Must contain at least one number")
      .regex(
        /[^A-Za-z0-9]/,
        "Must contain at least one special character"
      ),
    confirm_password: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

export type PasswordSetFormData = z.infer<typeof passwordSetSchema>;

/**
 * Helper function to get password strength score
 */
export function getPasswordStrength(password: string): {
  score: number;
  label: string;
  color: string;
} {
  let score = 0;
  const checks = [
    password.length >= 8,
    /[A-Z]/.test(password),
    /[a-z]/.test(password),
    /[0-9]/.test(password),
    /[^A-Za-z0-9]/.test(password),
  ];

  score = checks.filter(Boolean).length;

  const strengthMap: Record<number, { label: string; color: string }> = {
    0: { label: "Too weak", color: "bg-red-500" },
    1: { label: "Weak", color: "bg-red-400" },
    2: { label: "Fair", color: "bg-yellow-400" },
    3: { label: "Good", color: "bg-blue-400" },
    4: { label: "Strong", color: "bg-green-400" },
    5: { label: "Very Strong", color: "bg-green-500" },
  };

  return { score: score * 20, ...strengthMap[score] };
}

/**
 * Helper function to format validation errors
 */
export function formatZodErrors(error: z.ZodError): Record<string, string> {
  const formatted: Record<string, string> = {};
  error.issues.forEach((issue) => {
    const path = issue.path.join(".");
    formatted[path] = issue.message;
  });
  return formatted;
}
