import { ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';

interface BadgeProps {
  readonly children: ReactNode;
  readonly variant?:
    | 'default'
    | 'primary'
    | 'secondary'
    | 'outline'
    | 'info'
    | 'success'
    | 'danger'
    | 'purple';
  readonly icon?: LucideIcon;
  readonly className?: string;
}

export function Badge({ children, variant = 'default', icon: Icon, className = '' }: BadgeProps) {
  const variants = {
    default: 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300',
    primary:
      'bg-md-primary-container dark:bg-md-primary-container text-md-on-primary-container dark:text-md-on-primary-container',
    secondary: 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300',
    outline:
      'bg-transparent border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300',
    info: 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300',
    success: 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300',
    danger: 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300',
    purple: 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300',
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${variants[variant]} ${className} `}
    >
      {Icon && <Icon className="h-3 w-3" />}
      {children}
    </span>
  );
}
