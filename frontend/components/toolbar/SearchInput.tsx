'use client';

import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui';

interface SearchInputProps {
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly onSubmit: () => void;
  readonly onClear: () => void;
  readonly showFilters: boolean;
}

export function SearchInput({ value, onChange, onSubmit, onClear, showFilters }: SearchInputProps) {
  return (
    <div className="relative min-w-[200px] flex-1">
      <Input
        type="text"
        placeholder="Search jobs..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e: React.KeyboardEvent) => {
          if (e.key === 'Enter') {
            onSubmit();
          }
        }}
        icon={Search}
      />
      {value && (
        <button
          type="button"
          onClick={onClear}
          aria-label="Clear search"
          className="absolute top-1/2 right-8 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
        >
          <X className="h-4 w-4" />
        </button>
      )}
      <div className="group absolute top-1/2 right-2 -translate-y-1/2">
        <button
          type="button"
          className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
          aria-label="Search tips"
          title="Search tips"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </button>
        {!showFilters && (
          <div className="dark:border-md-outline dark:bg-md-surface-container dark:text-md-on-surface pointer-events-none invisible absolute top-6 right-0 z-50 w-64 rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-600 opacity-0 shadow-lg transition-opacity group-hover:pointer-events-auto group-hover:visible group-hover:opacity-100">
            <p className="dark:text-md-on-surface mb-2 font-medium text-slate-700">
              Search syntax:
            </p>
            <ul className="space-y-1">
              <li>
                <code className="dark:bg-md-surface-container-high rounded bg-slate-100 px-1">
                  &quot;exact phrase&quot;
                </code>{' '}
                - Exact match
              </li>
              <li>
                <code className="dark:bg-md-surface-container-high rounded bg-slate-100 px-1">
                  python AND remote
                </code>{' '}
                - Both terms
              </li>
              <li>
                <code className="dark:bg-md-surface-container-high rounded bg-slate-100 px-1">
                  python OR java
                </code>{' '}
                - Either term
              </li>
              <li>
                <code className="dark:bg-md-surface-container-high rounded bg-slate-100 px-1">
                  python NOT senior
                </code>{' '}
                - Exclude
              </li>
              <li>
                <code className="dark:bg-md-surface-container-high rounded bg-slate-100 px-1">
                  title:python
                </code>{' '}
                - Field search
              </li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
