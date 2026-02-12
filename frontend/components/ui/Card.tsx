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

interface CardHeaderProps {
  children: ReactNode;
  className?: string;
}

export function CardHeader({ children, className = "" }: CardHeaderProps) {
  return (
    <div
      className={`
        px-6 pt-6 pb-4 border-b border-slate-200 dark:border-md-outline-variant
        ${className}
      `}
    >
      {children}
    </div>
  );
}

interface CardTitleProps {
  children: ReactNode;
  className?: string;
}

export function CardTitle({ children, className = "" }: CardTitleProps) {
  return (
    <h3
      className={`
        text-xl font-bold text-slate-900 dark:text-md-on-surface
        ${className}
      `}
    >
      {children}
    </h3>
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

interface CardFooterProps {
  children: ReactNode;
  className?: string;
}

export function CardFooter({ children, className = "" }: CardFooterProps) {
  return (
    <div
      className={`
        px-6 pt-4 pb-6 border-t border-slate-200 dark:border-md-outline-variant
        ${className}
      `}
    >
      {children}
    </div>
  );
}
