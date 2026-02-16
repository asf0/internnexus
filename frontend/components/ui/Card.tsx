import { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`
        rounded-xl border border-slate-200 dark:border-md-outline-variant
        bg-white dark:bg-md-surface-container
        shadow-sm
        ${className}
      `}
    >
      {children}
    </div>
  );
}

interface CardContentProps {
  children: ReactNode;
  className?: string;
}

export function CardContent({ children, className = "" }: CardContentProps) {
  return (
    <div
      className={`
        px-6 py-4 text-slate-700 dark:text-md-on-surface-variant
        ${className}
      `}
    >
      {children}
    </div>
  );
}
