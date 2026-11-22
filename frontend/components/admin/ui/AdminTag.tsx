'use client';

import { ReactNode } from 'react';

interface AdminTagProps {
  readonly children: ReactNode;
  readonly color?: string;
  readonly className?: string;
}

const colorMap: Record<string, string> = {
  default: 'bg-surface-subtle text-foreground-secondary',
  blue: 'bg-blue-100 text-blue-700 dark:bg-accent/15 dark:text-accent',
  green: 'bg-green-100 text-green-700 dark:bg-success/15 dark:text-success',
  red: 'bg-red-100 text-red-700 dark:bg-surface-inset dark:text-danger',
  orange: 'bg-orange-100 text-orange-700 dark:bg-warning/15 dark:text-warning',
  purple: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  cyan: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300',
  gold: 'bg-yellow-100 text-yellow-700 dark:bg-warning/15 dark:text-warning',
  success: 'bg-green-100 text-green-700 dark:bg-success/15 dark:text-success',
  error: 'bg-red-100 text-red-700 dark:bg-surface-inset dark:text-danger',
  warning: 'bg-yellow-100 text-yellow-700 dark:bg-warning/15 dark:text-warning',
  processing: 'bg-blue-100 text-blue-700 dark:bg-accent/15 dark:text-accent',
};

export function AdminTag({ children, color = 'default', className = '' }: AdminTagProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${colorMap[color] || colorMap.default} ${className}`}
    >
      {children}
    </span>
  );
}
