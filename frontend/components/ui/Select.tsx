import { forwardRef, type SelectHTMLAttributes } from 'react';

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className = '', children, ...props }, ref) {
    return (
      <select
        ref={ref}
        className={`border-border bg-surface text-foreground focus:border-accent focus:ring-focus-ring min-h-10 w-full rounded-lg border px-3 py-2.5 text-sm focus:ring-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
        {...props}
      >
        {children}
      </select>
    );
  }
);
