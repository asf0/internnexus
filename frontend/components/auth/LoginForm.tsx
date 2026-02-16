"use client";

import { Mail, Loader2 } from "lucide-react";
import { Button, Input } from "@/components/ui";

interface LoginFormProps {
  isLoading: boolean;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
}

export function LoginForm({ isLoading, onSubmit }: LoginFormProps) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
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
  );
}
