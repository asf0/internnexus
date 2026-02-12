import { ReactNode } from "react";
import { Input } from "./Input";
import { LucideIcon } from "lucide-react";

interface FormFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  icon?: LucideIcon;
  placeholder?: string;
  type?: "text" | "password" | "email" | "number" | "url";
  helperText?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
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
