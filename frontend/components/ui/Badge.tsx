import { ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';

interface BadgeProps {
  readonly children: ReactNode;
  readonly variant?:
    'default' | 'primary' | 'secondary' | 'outline' | 'info' | 'success' | 'danger' | 'purple';
  readonly icon?: LucideIcon;
  readonly className?: string;
}

export function Badge({ children, variant = 'default', icon: Icon, className = '' }: BadgeProps) {
  const variants = {
    default: 'bg-surface-subtle text-foreground-secondary',
    primary: 'bg-accent/15 text-accent',
    secondary: 'bg-surface-subtle text-foreground-muted',
    outline: 'border border-border bg-transparent text-foreground-secondary',
    info: 'bg-blue-100 text-blue-700 dark:bg-accent/15 dark:text-accent',
    success: 'bg-green-100 text-green-700 dark:bg-success/15 dark:text-success',
    danger: 'bg-red-100 text-red-700 dark:bg-surface-inset dark:text-danger',
    purple: 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300',
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${variants[variant]} ${className}`}
    >
      {Icon && <Icon className="h-3 w-3" />}
      {children}
    </span>
  );
}
