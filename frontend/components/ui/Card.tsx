import { ReactNode } from 'react';

interface CardProps {
  readonly children: ReactNode;
  readonly className?: string;
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div className={`border-border bg-surface rounded-xl border shadow-sm ${className}`}>
      {children}
    </div>
  );
}

interface CardContentProps {
  readonly children: ReactNode;
  readonly className?: string;
}

export function CardContent({ children, className = '' }: CardContentProps) {
  return <div className={`text-foreground-secondary p-5 sm:p-6 ${className}`}>{children}</div>;
}

export function CardHeader({ children, className = '' }: CardContentProps) {
  return (
    <div
      className={`border-border flex items-start justify-between gap-4 border-b px-5 py-4 sm:px-6 ${className}`}
    >
      {children}
    </div>
  );
}

export function CardTitle({ children, className = '' }: CardContentProps) {
  return <h2 className={`text-foreground text-lg font-semibold ${className}`}>{children}</h2>;
}

export function CardDescription({ children, className = '' }: CardContentProps) {
  return <p className={`text-foreground-muted mt-1 text-sm ${className}`}>{children}</p>;
}
