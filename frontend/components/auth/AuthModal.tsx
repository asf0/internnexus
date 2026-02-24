"use client";

import { signIn } from "next-auth/react";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Modal } from "@/components/modals";
import { Alert } from "@/components/ui";
import { loginSchema, registrationSchema } from "@/lib/validation";
import { registerUser } from "@/app/actions/auth";
import { OAuthButtons } from "./OAuthButtons";
import { LoginForm } from "./LoginForm";
import { RegisterForm } from "./RegisterForm";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultMode?: "login" | "register";
  onAuthSuccess?: (applyWindow?: Window | null) => void;
  intent?: "default" | "apply";
  callbackUrl?: string;
}

export default function AuthModal({
  isOpen,
  onClose,
  defaultMode = "login",
  onAuthSuccess,
  intent = "default",
  callbackUrl,
}: AuthModalProps) {
  const [mode, setMode] = useState<"login" | "register">(defaultMode);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const router = useRouter();

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
      await signIn(provider, callbackUrl ? { callbackUrl } : undefined);
    } catch {
      setError("Failed to sign in. Please try again.");
      setIsLoading(false);
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    const continuationWindow = intent === "apply"
      ? window.open("", "_blank", "noopener,noreferrer")
      : null;

    const formData = new FormData(e.currentTarget);
    const data = {
      email: formData.get("email") as string,
      password: formData.get("password") as string,
    };

    const result = loginSchema.safeParse(data);
    if (!result.success) {
      continuationWindow?.close();
      setError(result.error.issues[0].message);
      setIsLoading(false);
      return;
    }

    try {
      const authResult = await signIn("credentials", {
        email: result.data.email,
        password: result.data.password,
        redirect: false,
      });

      if (authResult?.error) {
        continuationWindow?.close();
        setError("Invalid email or password");
        setIsLoading(false);
        return;
      }

      onAuthSuccess?.(continuationWindow);
      router.refresh();
      onClose();
    } catch {
      continuationWindow?.close();
      setError("An unexpected error occurred. Please try again.");
      setIsLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    const continuationWindow = intent === "apply"
      ? window.open("", "_blank", "noopener,noreferrer")
      : null;
    
    const formData = new FormData(e.currentTarget);
    const data = {
      name: formData.get("name") as string,
      email: formData.get("email") as string,
      password: password,
      confirm_password: confirmPassword,
    };

    const validationResult = registrationSchema.safeParse(data);
    if (!validationResult.success) {
      continuationWindow?.close();
      setError(validationResult.error.issues[0].message);
      return;
    }
    
    setIsLoading(true);

    try {
      const registerResult = await registerUser({
        email: validationResult.data.email,
        password: validationResult.data.password,
        name: validationResult.data.name,
      });

      if (!registerResult.success) {
        continuationWindow?.close();
        if (registerResult.errorType === "EMAIL_REGISTERED_WITH_OAUTH") {
          setError(
            `${registerResult.error} Please sign in with your OAuth provider or go to Settings to set a password.`
          );
        } else {
          setError(registerResult.error || "Registration failed. Please try again.");
        }
        setIsLoading(false);
        return;
      }

      const authResult = await signIn("credentials", {
        email: validationResult.data.email,
        password: validationResult.data.password,
        redirect: false,
      });

      if (authResult?.error) {
        continuationWindow?.close();
        setError("Account created but sign in failed. Please try signing in.");
        setIsLoading(false);
        return;
      }

      onAuthSuccess?.(continuationWindow);
      router.refresh();
      onClose();
    } catch {
      continuationWindow?.close();
      setError("An unexpected error occurred. Please try again.");
      setIsLoading(false);
    }
  };

  const toggleMode = () => {
    if (isLoading) return;
    setMode(mode === "login" ? "register" : "login");
    setError(null);
  };

  const isApplyIntent = intent === "apply";
  const title = mode === "login"
    ? (isApplyIntent ? "Sign in to apply" : "Welcome to InternNexus")
    : (isApplyIntent ? "Create an account to apply" : "Create your account");
  const subtitle = isApplyIntent
    ? "We will open the job application in a new tab right after sign in."
    : "Sign in to find your dream internship";
  const loginSubmitLabel = isApplyIntent ? "Sign in and continue" : "Sign in with Email";
  const registerSubmitLabel = isApplyIntent ? "Create account and continue" : "Create account";

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={<>
        {title}
        <p className="mt-1 text-sm font-normal text-slate-600 dark:text-md-on-surface-variant">
          {subtitle}
        </p>
      </>}
      size="md"
    >
      {error && (
        <Alert type="error" className="mb-4">
          {error}
        </Alert>
      )}

      <OAuthButtons isLoading={isLoading} onSignIn={handleOAuthSignIn} />

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

      {mode === "login" ? (
        <LoginForm
          isLoading={isLoading}
          onSubmit={handleLoginSubmit}
          submitLabel={loginSubmitLabel}
          autoFocusFirstField
        />
      ) : (
        <RegisterForm
          isLoading={isLoading}
          password={password}
          confirmPassword={confirmPassword}
          onPasswordChange={setPassword}
          onConfirmPasswordChange={setConfirmPassword}
          onSubmit={handleRegisterSubmit}
          submitLabel={registerSubmitLabel}
          autoFocusFirstField
        />
      )}

      <div className="mt-6 text-center">
        <p className="text-sm text-slate-600 dark:text-md-on-surface-variant">
          {mode === "login" ? (
            <>
              Don&apos;t have an account?{" "}
              <button
                onClick={toggleMode}
                disabled={isLoading}
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
                disabled={isLoading}
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
