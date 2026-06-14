import { InputHTMLAttributes } from 'react';
import { LucideIcon } from 'lucide-react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  readonly icon?: LucideIcon;
  readonly iconPosition?: 'left' | 'right';
  readonly error?: string;
}

export function Input({
  icon: Icon,
  iconPosition = 'left',
  error,
  className = '',
  ...props
}: InputProps) {
  return (
    <div className="relative w-full">
      {Icon && iconPosition === 'left' && (
        <Icon className="dark:text-md-on-surface-variant absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" />
      )}

      <input
        className={`dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface dark:placeholder-md-on-surface-variant focus:border-md-primary focus:ring-md-primary w-full rounded-lg border border-slate-300 bg-white text-sm text-slate-900 placeholder-slate-400 focus:ring-1 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 ${Icon && iconPosition === 'left' ? 'pl-10' : 'px-3'} ${Icon && iconPosition === 'right' ? 'pr-10' : ''} py-2.5 ${className} `}
        {...props}
      />

      {Icon && iconPosition === 'right' && (
        <Icon className="dark:text-md-on-surface-variant absolute top-1/2 right-3 h-4 w-4 -translate-y-1/2 text-slate-400" />
      )}

      {error && <p className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}
