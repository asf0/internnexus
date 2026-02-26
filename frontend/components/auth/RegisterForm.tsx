"use client";

import { UserPlus, Loader2 } from "lucide-react";
import { Button, Input } from "@/components/ui";
import { PasswordInput, calculateStrength } from "@/components/common";

interface RegisterFormProps {
  readonly isLoading: boolean;
  readonly password: string;
  readonly confirmPassword: string;
  readonly onPasswordChange: (password: string) => void;
  readonly onConfirmPasswordChange: (password: string) => void;
  readonly onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  readonly submitLabel?: string;
  readonly autoFocusFirstField?: boolean;
}

export function RegisterForm({
  isLoading,
  password,
  confirmPassword,
  onPasswordChange,
  onConfirmPasswordChange,
  onSubmit,
  submitLabel = "Create account",
  autoFocusFirstField = false,
}: RegisterFormProps) {
  const isSubmitDisabled =
    isLoading ||
    calculateStrength(password).score < 100 ||
    password !== confirmPassword;

  return (
    <form onSubmit={onSubmit} className="space-y-4">
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
          autoFocus={autoFocusFirstField}
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
        onChange={onPasswordChange}
        confirmValue={confirmPassword}
        onConfirmChange={onConfirmPasswordChange}
        showConfirmation={true}
        disabled={isLoading}
      />

      <Button
        type="submit"
        disabled={isSubmitDisabled}
        className="w-full"
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <UserPlus className="w-4 h-4" />
        )}
        {isLoading ? "Creating account..." : submitLabel}
      </Button>
    </form>
  );
}
