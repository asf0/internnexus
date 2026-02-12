"use client";

import { signIn, useSession } from "next-auth/react";
import { Github, Mail, UserPlus, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";
import PasswordInput, { calculateStrength } from "./PasswordInput";
import Modal from "./Modal";
import { Button, Input, Alert } from "./ui";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultMode?: "login" | "register";
}

const backendBaseUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export default function AuthModal({ isOpen, onClose, defaultMode = "login" }: AuthModalProps) {
  const [mode, setMode] = useState<"login" | "register">(defaultMode);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const { update } = useSession();

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setMode(defaultMode);
      setError(null);
      setIsLoading(false);
      setPassword("");
      setConfirmPassword("");
    }
  }, [isOpen, defaultMode]);

  const handleOAuthSignIn = async (provider: "github" | "google") => {
    setIsLoading(true);
    setError(null);
    try {
      await signIn(provider);
    } catch {
      setError("Failed to sign in. Please try again.");
      setIsLoading(false);
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    const formData = new FormData(e.currentTarget);
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;

    try {
      const result = await signIn("credentials", {
        email,
        password,
        redirect: false,
      });

      if (result?.error) {
        setError("Invalid email or password");
        setIsLoading(false);
        return;
      }

      // Update session and close modal
      await update();
      onClose();
    } catch {
      setError("An unexpected error occurred. Please try again.");
      setIsLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    
    // Validate password strength
    const strength = calculateStrength(password);
    if (strength.score < 100) {
      setError("Please meet all password requirements");
      return;
    }
    
    // Validate password confirmation
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    
    setIsLoading(true);

    const formData = new FormData(e.currentTarget);
    const email = formData.get("email") as string;
    const name = formData.get("name") as string;

    try {
      const response = await fetch(`${backendBaseUrl}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name }),
      });

      const data = await response.json();

      if (!response.ok) {
        const detail = data.detail || {};
        if (detail.error === "EMAIL_REGISTERED_WITH_OAUTH") {
          setError(
            `${detail.message} Please sign in with your OAuth provider or go to Settings to set a password.`
          );
        } else {
          setError(detail.message || "Registration failed. Please try again.");
        }
        setIsLoading(false);
        return;
      }

      // Registration successful - sign in with credentials
      const result = await signIn("credentials", {
        email,
        password,
        redirect: false,
      });

      if (result?.error) {
        setError("Account created but sign in failed. Please try signing in.");
        setIsLoading(false);
        return;
      }

      // Update session and close modal
      await update();
      onClose();
    } catch {
      setError("An unexpected error occurred. Please try again.");
      setIsLoading(false);
    }
  };

  const toggleMode = () => {
    setMode(mode === "login" ? "register" : "login");
    setError(null);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={<>
        Welcome to InternNexus
        <p className="mt-1 text-sm font-normal text-slate-600 dark:text-md-on-surface-variant">
          Sign in to find your dream internship
        </p>
      </>}
      size="md"
    >
      {/* Error Message */}
      {error && (
        <Alert type="error" className="mb-4">
          {error}
        </Alert>
      )}

      {/* OAuth Buttons */}
      <div className="space-y-3 mb-6">
        <Button
          variant="secondary"
          onClick={() => handleOAuthSignIn("github")}
          disabled={isLoading}
          className="w-full"
        >
          <Github className="w-5 h-5" />
          Continue with GitHub
        </Button>

        <Button
          variant="secondary"
          onClick={() => handleOAuthSignIn("google")}
          disabled={isLoading}
          className="w-full"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              fill="currentColor"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="currentColor"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="currentColor"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="currentColor"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          Continue with Google
        </Button>
      </div>

      {/* Divider */}
      <div className="relative mb-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-slate-300 dark:border-md-outline-variant" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-white dark:bg-md-surface-container text-slate-500 dark:text-md-on-surface-variant">
            Or continue with email
          </span>
        </div>
      </div>

      {/* Forms */}
      {mode === "login" ? (
        <form onSubmit={handleLoginSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1"
            >
              Email address
            </label>
            <Input
              id="email"
              name="email"
              type="email"
              required
              disabled={isLoading}
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1"
            >
              Password
            </label>
            <Input
              id="password"
              name="password"
              type="password"
              required
              disabled={isLoading}
              placeholder="••••••••"
            />
          </div>

          <Button
            type="submit"
            disabled={isLoading}
            className="w-full"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Mail className="w-4 h-4" />
            )}
            {isLoading ? "Signing in..." : "Sign in with Email"}
          </Button>
        </form>
      ) : (
        <form onSubmit={handleRegisterSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="name"
              className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1"
            >
              Full name
            </label>
            <Input
              id="name"
              name="name"
              type="text"
              required
              disabled={isLoading}
              placeholder="John Doe"
            />
          </div>

          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1"
            >
              Email address
            </label>
            <Input
              id="email"
              name="email"
              type="email"
              required
              disabled={isLoading}
              placeholder="you@example.com"
            />
          </div>

          <PasswordInput
            value={password}
            onChange={setPassword}
            confirmValue={confirmPassword}
            onConfirmChange={setConfirmPassword}
            showConfirmation={true}
            disabled={isLoading}
          />

          <Button
            type="submit"
            disabled={isLoading || calculateStrength(password).score < 100 || password !== confirmPassword}
            className="w-full"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <UserPlus className="w-4 h-4" />
            )}
            {isLoading ? "Creating account..." : "Create account"}
          </Button>
        </form>
      )}

      {/* Footer Link */}
      <div className="mt-6 text-center">
        <p className="text-sm text-slate-600 dark:text-md-on-surface-variant">
          {mode === "login" ? (
            <>
              Don&apos;t have an account?{" "}
              <button
                onClick={toggleMode}
                className="font-medium text-md-primary hover:text-md-on-primary-container dark:text-md-primary dark:hover:text-md-primary-container transition-colors"
              >
                Sign up
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button
                onClick={toggleMode}
                className="font-medium text-md-primary hover:text-md-on-primary-container dark:text-md-primary dark:hover:text-md-primary-container transition-colors"
              >
                Sign in
              </button>
            </>
          )}
        </p>
      </div>
    </Modal>
  );
}
