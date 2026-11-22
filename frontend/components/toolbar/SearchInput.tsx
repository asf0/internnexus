'use client';

import { Search, X } from 'lucide-react';
import { useEffect, useId, useRef, useState } from 'react';
import { Input } from '@/components/ui';

interface SearchInputProps {
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly onSubmit: () => void;
  readonly onClear: () => void;
  readonly showFilters: boolean;
}

export function SearchInput({ value, onChange, onSubmit, onClear, showFilters }: SearchInputProps) {
  const [showTips, setShowTips] = useState(false);
  const tipsId = useId();
  const tipsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (showFilters) {
      setShowTips(false);
    }
  }, [showFilters]);

  useEffect(() => {
    if (!showTips) return;

    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!tipsRef.current?.contains(event.target as Node)) {
        setShowTips(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowTips(false);
      }
    };

    document.addEventListener('mousedown', closeOnOutsideClick);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [showTips]);

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
          className="text-foreground-muted hover:text-foreground absolute top-1/2 right-8 -translate-y-1/2"
        >
          <X className="h-4 w-4" />
        </button>
      )}
      <div ref={tipsRef} className="absolute top-1/2 right-2 -translate-y-1/2">
        <button
          type="button"
          onClick={() => setShowTips((isVisible) => !isVisible)}
          className="text-foreground-muted hover:text-foreground"
          aria-label="Search tips"
          aria-expanded={showTips}
          aria-controls={tipsId}
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
        {showTips && !showFilters && (
          <div
            id={tipsId}
            role="note"
            className="border-border bg-surface text-foreground-secondary absolute top-7 right-0 z-50 w-64 rounded-lg border p-3 text-xs shadow-lg"
          >
            <p className="text-foreground mb-2 font-medium">Search syntax:</p>
            <ul className="space-y-1">
              <li>
                <code className="bg-surface-subtle rounded px-1">&quot;exact phrase&quot;</code> -
                Exact match
              </li>
              <li>
                <code className="bg-surface-subtle rounded px-1">python AND remote</code> - Both
                terms
              </li>
              <li>
                <code className="bg-surface-subtle rounded px-1">python OR java</code> - Either term
              </li>
              <li>
                <code className="bg-surface-subtle rounded px-1">python NOT senior</code> - Exclude
              </li>
              <li>
                <code className="bg-surface-subtle rounded px-1">title:python</code> - Field search
              </li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
