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
}

export default function AuthModal({ isOpen, onClose, defaultMode = "login" }: AuthModalProps) {
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
    const data = {
      email: formData.get("email") as string,
      password: formData.get("password") as string,
    };

    const result = loginSchema.safeParse(data);
    if (!result.success) {
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
        setError("Invalid email or password");
        setIsLoading(false);
        return;
      }

      router.refresh();
      onClose();
    } catch {
      setError("An unexpected error occurred. Please try again.");
      setIsLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    
    const formData = new FormData(e.currentTarget);
    const data = {
      name: formData.get("name") as string,
      email: formData.get("email") as string,
      password: password,
      confirm_password: confirmPassword,
    };

    const validationResult = registrationSchema.safeParse(data);
    if (!validationResult.success) {
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
        setError("Account created but sign in failed. Please try signing in.");
        setIsLoading(false);
        return;
      }

      router.refresh();
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
        <LoginForm isLoading={isLoading} onSubmit={handleLoginSubmit} />
      ) : (
        <RegisterForm
          isLoading={isLoading}
          password={password}
          confirmPassword={confirmPassword}
          onPasswordChange={setPassword}
          onConfirmPasswordChange={setConfirmPassword}
          onSubmit={handleRegisterSubmit}
        />
      )}

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
