'use client';

import { UserPlus, Loader2 } from 'lucide-react';
import { Button, Input } from '@/components/ui';
import { PasswordInput, calculateStrength } from '@/components/common';

interface RegisterFormProps {
  readonly isLoading: boolean;
  readonly password: string;
  readonly confirmPassword: string;
  readonly onPasswordChange: (password: string) => void;
  readonly onConfirmPasswordChange: (password: string) => void;
  readonly onSubmit: (e: React.SyntheticEvent<HTMLFormElement, SubmitEvent>) => void;
  readonly submitLabel?: string;
}

export function RegisterForm({
  isLoading,
  password,
  confirmPassword,
  onPasswordChange,
  onConfirmPasswordChange,
  onSubmit,
  submitLabel = 'Create account',
}: RegisterFormProps) {
  const isSubmitDisabled =
    isLoading || calculateStrength(password).score < 100 || password !== confirmPassword;

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label htmlFor="name" className="text-foreground-secondary mb-1 block text-sm font-medium">
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
        <label htmlFor="email" className="text-foreground-secondary mb-1 block text-sm font-medium">
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

      <Button type="submit" disabled={isSubmitDisabled} className="w-full">
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <UserPlus className="h-4 w-4" />
        )}
        {isLoading ? 'Creating account...' : submitLabel}
      </Button>
    </form>
  );
}
