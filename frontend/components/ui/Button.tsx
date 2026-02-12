import { ReactNode, ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
  children: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  children,
  className = "",
  ...props
}: ButtonProps) {
  const baseStyles =
    "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-md-primary focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";

  const variants = {
    primary:
      "bg-md-primary text-white hover:bg-md-primary-container border border-transparent",
    secondary:
      "bg-white dark:bg-md-surface-container text-slate-700 dark:text-md-on-surface border border-slate-300 dark:border-md-outline-variant hover:bg-slate-50 dark:hover:bg-md-surface-container-high",
    outline:
      "bg-transparent text-slate-700 dark:text-md-on-surface-variant border border-slate-300 dark:border-md-outline-variant hover:bg-slate-50 dark:hover:bg-md-surface-container",
    ghost:
      "bg-transparent text-slate-600 dark:text-md-on-surface-variant hover:text-slate-900 dark:hover:text-md-on-surface hover:bg-slate-100 dark:hover:bg-md-surface-container-high",
  };

  const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2.5 text-sm",
    lg: "px-6 py-3 text-base",
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
