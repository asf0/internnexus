import { ReactNode } from 'react';

interface CardProps {
  readonly children: ReactNode;
  readonly className?: string;
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div
      className={`dark:border-md-outline-variant dark:bg-md-surface-container rounded-xl border border-slate-200 bg-white shadow-sm ${className} `}
    >
      {children}
    </div>
  );
}

interface CardContentProps {
  readonly children: ReactNode;
  readonly className?: string;
}

export function CardContent({ children, className = '' }: CardContentProps) {
  return (
    <div className={`dark:text-md-on-surface-variant px-6 py-4 text-slate-700 ${className} `}>
      {children}
    </div>
  );
}
