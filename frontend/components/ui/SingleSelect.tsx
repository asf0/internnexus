'use client';

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check } from 'lucide-react';

interface SingleSelectProps {
  readonly options: { value: string; label: string }[];
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly placeholder: string;
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

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedOption = options.find((opt) => opt.value === value);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="dark:border-md-outline-variant dark:bg-md-surface-container flex min-h-[44px] w-full cursor-pointer items-center justify-between rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span
          className={
            selectedOption
              ? 'dark:text-md-on-surface text-slate-900'
              : 'dark:text-md-on-surface text-slate-400'
          }
        >
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown
          size={16}
          className={`ml-2 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {isOpen && (
        <div className="dark:border-md-outline-variant dark:bg-md-surface-container absolute z-40 mt-1 w-full overflow-hidden rounded-lg border border-slate-300 bg-white shadow-lg">
          <div className="max-h-52 overflow-y-auto">
            <button
              type="button"
              onClick={() => {
                onChange('');
              }}
              className="dark:hover:bg-md-surface-container-high flex cursor-pointer items-center justify-between px-3 py-2 text-sm hover:bg-slate-50"
            >
              <span className="dark:text-md-on-surface text-slate-900">{placeholder}</span>
              {!value && <Check size={16} className="dark:text-md-on-surface text-slate-900" />}
            </button>
            {options.map((option) => (
              <button
                type="button"
                key={option.value}
                onClick={() => {
                  onChange(option.value);
                }}
                className="dark:hover:bg-md-surface-container-high flex cursor-pointer items-center justify-between px-3 py-2 text-sm hover:bg-slate-50"
              >
                <span className="dark:text-md-on-surface text-slate-900">{option.label}</span>
                {value === option.value && (
                  <Check size={16} className="dark:text-md-on-surface text-slate-900" />
                )}
              </button>
            ))}
          </div>
          <div className="dark:border-md-outline-variant dark:bg-md-surface-container flex items-center justify-between border-t border-slate-200 bg-white p-2">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onChange('');
              }}
              disabled={!value}
              className="dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high rounded px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Clear
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setIsOpen(false);
              }}
              className="bg-md-primary rounded px-2 py-1 text-xs font-medium text-white hover:opacity-90"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
