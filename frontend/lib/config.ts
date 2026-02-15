// Centralized configuration
export const BACKEND_URL = process.env.BACKEND_URL || 
                           process.env.NEXT_PUBLIC_API_URL || 
                           "http://localhost:8000";

export const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || "https://jobfinder.asf0.dev";
