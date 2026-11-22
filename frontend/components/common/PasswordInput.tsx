'use client';

import { useState, useMemo } from 'react';
import { Eye, EyeOff, Check, X } from 'lucide-react';
import { Input } from '@/components/ui';

interface Requirement {
  label: string;
  met: boolean;
}

interface PasswordStrength {
  score: number;
  requirements: Requirement[];
  level: 'weak' | 'fair' | 'good' | 'strong';
}

interface PasswordInputProps {
  value: string;
  onChange: (value: string) => void;
  confirmValue?: string;
  onConfirmChange?: (value: string) => void;
  showConfirmation?: boolean;
  label?: string;
  confirmLabel?: string;
  placeholder?: string;
  disabled?: boolean;
  id?: string;
  showStrengthIndicator?: boolean;
  showRequirements?: boolean;
}

const SPECIAL_CHARS = '!@#$%^&*()_+-=[]{}|;:,.<>?';

function escapeRegex(value: string): string {
  return value.replace(/[\\^$.*+?()[\]{}|/-]/g, String.raw`\$&`);
}

const SPECIAL_CHAR_REGEX = new RegExp(`[${escapeRegex(SPECIAL_CHARS)}]`);

function calculateStrength(password: string): PasswordStrength {
  const requirements: Requirement[] = [
    { label: '8+ characters', met: password.length >= 8 },
    { label: '1 uppercase letter', met: /[A-Z]/.test(password) },
    { label: '1 lowercase letter', met: /[a-z]/.test(password) },
    { label: '1 number', met: /\d/.test(password) },
    {
      label: '1 special character',
      met: SPECIAL_CHAR_REGEX.test(password),
    },
  ];

  const metCount = requirements.filter((r) => r.met).length;
  const score = (metCount / 5) * 100;

  let level: 'weak' | 'fair' | 'good' | 'strong';
  if (score < 40) level = 'weak';
  else if (score < 70) level = 'fair';
  else if (score < 100) level = 'good';
  else level = 'strong';

  return { score, requirements, level };
}

function getStrengthColor(level: PasswordStrength['level']): string {
  switch (level) {
    case 'weak':
      return 'bg-danger';
    case 'fair':
      return 'bg-warning';
    case 'good':
      return 'bg-accent';
    case 'strong':
      return 'bg-success';
  }
}

function getStrengthTextColor(level: PasswordStrength['level']): string {
  switch (level) {
    case 'weak':
      return 'text-danger';
    case 'fair':
      return 'text-warning';
    case 'good':
      return 'text-accent';
    case 'strong':
      return 'text-success';
  }
}

export default function PasswordInput({
  value,
  onChange,
  confirmValue = '',
  onConfirmChange,
  showConfirmation = false,
  label = 'Password',
  confirmLabel = 'Confirm Password',
  placeholder = '••••••••',
  disabled = false,
  id = 'password',
  showStrengthIndicator = true,
  showRequirements = true,
}: Readonly<PasswordInputProps>) {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const strength = useMemo(() => calculateStrength(value), [value]);
  const passwordsMatch = !showConfirmation || value === confirmValue;
  const confirmPasswordTouched = showConfirmation && confirmValue.length > 0;

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value);
  };

  const handleConfirmChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onConfirmChange?.(e.target.value);
  };

  return (
    <div className="space-y-4">
      {/* Password Field */}
      <div>
        <label htmlFor={id} className="text-foreground-secondary mb-1 block text-sm font-medium">
          {label}
        </label>
        <div className="relative">
          <Input
            id={id}
            type={showPassword ? 'text' : 'password'}
            value={value}
            onChange={handlePasswordChange}
            disabled={disabled}
            className="pr-10"
            placeholder={placeholder}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="text-foreground-muted hover:text-foreground absolute top-1/2 right-3 z-10 -translate-y-1/2 transition-colors"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>

        {/* Strength Indicator */}
        {showStrengthIndicator && value.length > 0 && (
          <div className="mt-2">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-foreground-muted text-xs">Password strength</span>
              <span
                className={`text-xs font-medium capitalize ${getStrengthTextColor(strength.level)}`}
              >
                {strength.level}
              </span>
            </div>
            <div className="bg-surface-subtle h-2 overflow-hidden rounded-full">
              <div
                className={`h-full transition-all duration-300 ${getStrengthColor(strength.level)}`}
                style={{ width: `${strength.score}%` }}
              />
            </div>
          </div>
        )}

        {/* Requirements Checklist */}
        {showRequirements && (
          <div className="mt-3 space-y-1">
            {strength.requirements.map((req) => (
              <div key={req.label} className="flex items-center gap-2 text-xs">
                {req.met ? (
                  <Check className="text-success h-3 w-3" />
                ) : (
                  <X className="text-foreground-muted h-3 w-3" />
                )}
                <span className={req.met ? 'text-success' : 'text-foreground-muted'}>
                  {req.label}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Confirm Password Field */}
      {showConfirmation && (
        <div>
          <label
            htmlFor={`${id}-confirm`}
            className="text-foreground-secondary mb-1 block text-sm font-medium"
          >
            {confirmLabel}
          </label>
          <div className="relative">
            <Input
              id={`${id}-confirm`}
              type={showConfirmPassword ? 'text' : 'password'}
              value={confirmValue}
              onChange={handleConfirmChange}
              disabled={disabled}
              className="pr-10"
              error={
                confirmPasswordTouched && !passwordsMatch ? 'Passwords do not match' : undefined
              }
              placeholder={placeholder}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="text-foreground-muted hover:text-foreground absolute top-5 right-3 z-10 -translate-y-1/2 transition-colors"
              aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
            >
              {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export { calculateStrength, SPECIAL_CHARS };
export type { PasswordStrength, Requirement };
