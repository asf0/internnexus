import { ReactNode, InputHTMLAttributes } from "react";
import { LucideIcon } from "lucide-react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  readonly icon?: LucideIcon;
  readonly iconPosition?: "left" | "right";
  readonly error?: string;
}

export function Input({
  icon: Icon,
  iconPosition = "left",
  error,
  className = "",
  ...props
}: InputProps) {
  return (
    <div className="relative w-full">
      {Icon && iconPosition === "left" && (
        <Icon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 dark:text-md-on-surface-variant" />
      )}

      <input
        className={`
          w-full rounded-lg border border-slate-300 dark:border-md-outline-variant
          bg-white dark:bg-md-surface-container
          text-sm text-slate-900 dark:text-md-on-surface
          placeholder-slate-400 dark:placeholder-md-on-surface-variant
          focus:border-md-primary focus:outline-none focus:ring-1 focus:ring-md-primary
          disabled:opacity-50 disabled:cursor-not-allowed
          ${Icon && iconPosition === "left" ? "pl-10" : "px-3"}
          ${Icon && iconPosition === "right" ? "pr-10" : ""}
          py-2.5
          ${className}
        `}
        {...props}
      />

      {Icon && iconPosition === "right" && (
        <Icon className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 dark:text-md-on-surface-variant" />
      )}

      {error && (
        <p className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}
