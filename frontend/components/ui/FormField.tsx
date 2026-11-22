import { useId } from 'react';
import { Input } from './Input';
import { LucideIcon } from 'lucide-react';

interface FormFieldProps {
  readonly label: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly icon?: LucideIcon;
  readonly placeholder?: string;
  readonly type?: 'text' | 'password' | 'email' | 'number' | 'url';
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
  type = 'text',
  helperText,
  error,
  required = false,
  disabled = false,
}: FormFieldProps) {
  const inputId = useId();
  const descriptionId = helperText || error ? `${inputId}-description` : undefined;
  const labelClasses = 'text-foreground-secondary mb-1.5 block text-sm font-medium';

  return (
    <div>
      <label htmlFor={inputId} className={labelClasses}>
        {label}
        {required && <span className="text-danger ml-1">*</span>}
      </label>
      <Input
        id={inputId}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        icon={icon}
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        aria-invalid={!!error}
        aria-describedby={descriptionId}
      />
      {helperText && !error && (
        <p id={descriptionId} className="text-foreground-muted mt-1.5 text-sm">
          {helperText}
        </p>
      )}
      {error && (
        <p id={descriptionId} className="text-danger mt-1.5 text-sm">
          {error}
        </p>
      )}
    </div>
  );
}
