"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronDown, Check } from "lucide-react";

interface SingleSelectProps {
  options: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}

export function SingleSelect({ options, value, onChange, placeholder }: SingleSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedOption = options.find((opt) => opt.value === value);

  return (
    <div ref={ref} className="relative">
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex min-h-[38px] cursor-pointer items-center justify-between rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-md-outline-variant dark:bg-md-surface-container"
      >
        <span
          className={
            selectedOption
              ? "text-slate-900 dark:text-md-on-surface"
              : "text-slate-400 dark:text-md-on-surface"
          }
        >
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown
          size={16}
          className={`ml-2 text-slate-400 transition-transform ${isOpen ? "rotate-180" : ""}`}
        />
      </div>

      {isOpen && (
        <div className="absolute z-40 mt-1 w-full overflow-hidden rounded-lg border border-slate-300 bg-white shadow-lg dark:border-md-outline-variant dark:bg-md-surface-container">
          <div className="max-h-52 overflow-y-auto">
            <div
              onClick={() => {
                onChange("");
              }}
              className="flex cursor-pointer items-center justify-between px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-md-surface-container-high"
            >
              <span className="text-slate-900 dark:text-md-on-surface">{placeholder}</span>
              {!value && (
                <Check size={16} className="text-slate-900 dark:text-md-on-surface" />
              )}
            </div>
            {options.map((option) => (
              <div
                key={option.value}
                onClick={() => {
                  onChange(option.value);
                }}
                className="flex cursor-pointer items-center justify-between px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-md-surface-container-high"
              >
                <span className="text-slate-900 dark:text-md-on-surface">{option.label}</span>
                {value === option.value && (
                  <Check size={16} className="text-slate-900 dark:text-md-on-surface" />
                )}
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between border-t border-slate-200 bg-white p-2 dark:border-md-outline-variant dark:bg-md-surface-container">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onChange("");
              }}
              disabled={!value}
              className="rounded px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high"
            >
              Clear
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setIsOpen(false);
              }}
              className="rounded bg-md-primary px-2 py-1 text-xs font-medium text-white hover:opacity-90"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
