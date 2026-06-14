'use client';

import { Mail, Loader2 } from 'lucide-react';
import { Button, Input } from '@/components/ui';

interface LoginFormProps {
  readonly isLoading: boolean;
  readonly onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  readonly submitLabel?: string;
  readonly autoFocusFirstField?: boolean;
}

export function LoginForm({
  isLoading,
  onSubmit,
  submitLabel = 'Sign in with Email',
  autoFocusFirstField = false,
}: LoginFormProps) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label
          htmlFor="email"
          className="dark:text-md-on-surface-variant mb-1 block text-sm font-medium text-slate-700"
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
          autoFocus={autoFocusFirstField}
        />
      </div>

      <div>
        <label
          htmlFor="password"
          className="dark:text-md-on-surface-variant mb-1 block text-sm font-medium text-slate-700"
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
        {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4" />}
        {isLoading ? 'Signing in...' : submitLabel}
      </Button>
    </form>
  );
}
