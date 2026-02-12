"use client";

import { useState, useMemo } from "react";
import { Eye, EyeOff, Check, X } from "lucide-react";

interface Requirement {
  label: string;
  met: boolean;
}

interface PasswordStrength {
  score: number;
  requirements: Requirement[];
  level: "weak" | "fair" | "good" | "strong";
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

const SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?";

function calculateStrength(password: string): PasswordStrength {
  const requirements: Requirement[] = [
    { label: "8+ characters", met: password.length >= 8 },
    { label: "1 uppercase letter", met: /[A-Z]/.test(password) },
    { label: "1 lowercase letter", met: /[a-z]/.test(password) },
    { label: "1 number", met: /[0-9]/.test(password) },
    { label: "1 special character", met: new RegExp(`[${SPECIAL_CHARS.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, "\\$")}]`).test(password) },
  ];

  const metCount = requirements.filter((r) => r.met).length;
  const score = (metCount / 5) * 100;

  let level: "weak" | "fair" | "good" | "strong";
  if (score < 40) level = "weak";
  else if (score < 70) level = "fair";
  else if (score < 100) level = "good";
  else level = "strong";

  return { score, requirements, level };
}

function getStrengthColor(level: PasswordStrength["level"]): string {
  switch (level) {
    case "weak":
      return "bg-red-500";
    case "fair":
      return "bg-yellow-500";
    case "good":
      return "bg-blue-500";
    case "strong":
      return "bg-green-500";
  }
}

function getStrengthTextColor(level: PasswordStrength["level"]): string {
  switch (level) {
    case "weak":
      return "text-red-600 dark:text-red-400";
    case "fair":
      return "text-yellow-600 dark:text-yellow-400";
    case "good":
      return "text-blue-600 dark:text-blue-400";
    case "strong":
      return "text-green-600 dark:text-green-400";
  }
}

export default function PasswordInput({
  value,
  onChange,
  confirmValue = "",
  onConfirmChange,
  showConfirmation = false,
  label = "Password",
  confirmLabel = "Confirm Password",
  placeholder = "••••••••",
  disabled = false,
  id = "password",
  showStrengthIndicator = true,
  showRequirements = true,
}: PasswordInputProps) {
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
        <label
          htmlFor={id}
          className="block text-sm font-medium text-slate-700 dark:text-slate-400 mb-1"
        >
          {label}
        </label>
        <div className="relative">
          <input
            id={id}
            type={showPassword ? "text" : "password"}
            value={value}
            onChange={handlePasswordChange}
            disabled={disabled}
            className="block w-full px-3 py-2 pr-10 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-slate-800 dark:text-slate-100 disabled:opacity-50"
            placeholder={placeholder}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-100-variant transition-colors"
            tabIndex={-1}
          >
            {showPassword ? (
              <EyeOff className="w-4 h-4" />
            ) : (
              <Eye className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Strength Indicator */}
        {showStrengthIndicator && value.length > 0 && (
          <div className="mt-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-500 dark:text-slate-400">
                Password strength
              </span>
              <span
                className={`text-xs font-medium capitalize ${getStrengthTextColor(
                  strength.level
                )}`}
              >
                {strength.level}
              </span>
            </div>
            <div className="h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${getStrengthColor(
                  strength.level
                )}`}
                style={{ width: `${strength.score}%` }}
              />
            </div>
          </div>
        )}

        {/* Requirements Checklist */}
        {showRequirements && (
          <div className="mt-3 space-y-1">
            {strength.requirements.map((req, index) => (
              <div key={index} className="flex items-center gap-2 text-xs">
                {req.met ? (
                  <Check className="w-3 h-3 text-green-500" />
                ) : (
                  <X className="w-3 h-3 text-slate-400" />
                )}
                <span
                  className={
                    req.met
                      ? "text-green-600 dark:text-green-400"
                      : "text-slate-500 dark:text-slate-400"
                  }
                >
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
            className="block text-sm font-medium text-slate-700 dark:text-slate-400 mb-1"
          >
            {confirmLabel}
          </label>
          <div className="relative">
            <input
              id={`${id}-confirm`}
              type={showConfirmPassword ? "text" : "password"}
              value={confirmValue}
              onChange={handleConfirmChange}
              disabled={disabled}
              className={`block w-full px-3 py-2 pr-10 border rounded-lg shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-slate-800 dark:text-slate-100 disabled:opacity-50 ${
                confirmPasswordTouched && !passwordsMatch
                  ? "border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500"
                  : "border-slate-300 dark:border-slate-700"
              }`}
              placeholder={placeholder}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-100-variant transition-colors"
              tabIndex={-1}
            >
              {showConfirmPassword ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
          {confirmPasswordTouched && !passwordsMatch && (
            <p className="mt-1 text-xs text-red-600 dark:text-red-400">
              Passwords do not match
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export { calculateStrength, SPECIAL_CHARS };
export type { PasswordStrength, Requirement };
