'use client';

import { Loader2 } from 'lucide-react';
import { Button, Input } from '@/components/ui';

interface LoginFormProps {
  readonly isLoading: boolean;
  readonly onSubmit: (e: React.SyntheticEvent<HTMLFormElement, SubmitEvent>) => void;
  readonly submitLabel?: string;
}

export function LoginForm({
  isLoading,
  onSubmit,
  submitLabel = 'Sign in with Email',
}: LoginFormProps) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
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

      <div>
        <label
          htmlFor="password"
          className="text-foreground-secondary mb-1 block text-sm font-medium"
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

      <Button type="submit" disabled={isLoading} className="w-full">
        {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
        {isLoading ? 'Signing in...' : submitLabel}
      </Button>
    </form>
  );
}
