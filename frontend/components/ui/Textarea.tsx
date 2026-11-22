import { forwardRef, type TextareaHTMLAttributes } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  readonly error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className = '', error, ...props },
  ref
) {
  return (
    <div className="w-full">
      <textarea
        ref={ref}
        aria-invalid={error ? true : props['aria-invalid']}
        className={`border-border bg-surface text-foreground placeholder:text-foreground-muted focus:border-accent focus:ring-focus-ring min-h-24 w-full resize-y rounded-lg border px-3 py-2.5 text-sm focus:ring-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 ${error ? 'border-danger' : ''} ${className}`}
        {...props}
      />
      {error && <p className="text-danger mt-1.5 text-sm">{error}</p>}
    </div>
  );
});
