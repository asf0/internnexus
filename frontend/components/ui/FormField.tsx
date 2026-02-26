import { ReactNode } from "react";
import { Input } from "./Input";
import { LucideIcon } from "lucide-react";

interface FormFieldProps {
  readonly label: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly icon?: LucideIcon;
  readonly placeholder?: string;
  readonly type?: "text" | "password" | "email" | "number" | "url";
  readonly helperText?: string;
  readonly error?: string;
  readonly required?: boolean;
  readonly disabled?: boolean;
}

export function FormField({
  label,
  value,
  onChange,
  icon,
  placeholder,
  type = "text",
  helperText,
  error,
  required = false,
  disabled = false,
}: FormFieldProps) {
  const labelClasses = "block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1";

  return (
    <div>
      <label className={labelClasses}>
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <Input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        icon={icon}
        placeholder={placeholder}
        disabled={disabled}
      />
      {helperText && !error && (
        <p className="mt-1 text-sm text-slate-500 dark:text-md-on-surface-variant/70">{helperText}</p>
      )}
      {error && (
        <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}
