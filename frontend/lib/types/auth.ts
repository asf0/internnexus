// Authentication-related types

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    name: string | null;
    image: string | null;
  };
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string | null;
}

export interface OAuthCallbackRequest {
  provider: 'google' | 'github';
  provider_account_id: string;
  email: string;
  name: string | null;
  image: string | null;
  access_token: string;
  refresh_token: string | null;
  expires_at: string | null;
}

export interface SetPasswordRequest {
  password: string;
}

export interface ChangePasswordRequest {
  current_password?: string | null;
  new_password: string;
}
