import { z } from "zod";

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

export const loginSchema = z.object({
  email: z
    .string()
    .min(1, "Email is required")
    .email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
});

export type LoginFormData = z.infer<typeof loginSchema>;
