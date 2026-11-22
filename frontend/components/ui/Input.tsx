import { forwardRef, InputHTMLAttributes } from 'react';
import { LucideIcon } from 'lucide-react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  readonly icon?: LucideIcon;
  readonly iconPosition?: 'left' | 'right';
  readonly error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { icon: Icon, iconPosition = 'left', error, className = '', ...props },
  ref
) {
  return (
    <div className="relative w-full">
      {Icon && iconPosition === 'left' && (
        <Icon className="text-foreground-muted pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
      )}

      <input
        ref={ref}
        {...props}
        aria-invalid={error ? true : props['aria-invalid']}
        className={`border-border bg-surface text-foreground placeholder:text-foreground-muted focus:border-accent focus:ring-focus-ring w-full rounded-lg border text-sm focus:ring-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 ${error ? 'border-danger' : ''} ${Icon && iconPosition === 'left' ? 'pl-10' : 'px-3'} ${Icon && iconPosition === 'right' ? 'pr-10' : ''} py-2.5 ${className}`}
      />

      {Icon && iconPosition === 'right' && (
        <Icon className="text-foreground-muted pointer-events-none absolute top-1/2 right-3 h-4 w-4 -translate-y-1/2" />
      )}

      {error && <p className="text-danger mt-1 text-xs">{error}</p>}
    </div>
  );
});
