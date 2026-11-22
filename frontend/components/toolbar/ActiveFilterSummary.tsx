'use client';

import { X } from 'lucide-react';

export interface ActiveFilterItem {
  readonly id: string;
  readonly label: string;
  readonly onRemove: () => void;
}

interface ActiveFilterSummaryProps {
  readonly items: ActiveFilterItem[];
  readonly onClearAll?: () => void;
}

export function ActiveFilterSummary({ items, onClearAll }: ActiveFilterSummaryProps) {
  if (items.length === 0) return null;

  return (
    <fieldset className="flex flex-wrap items-center gap-2" aria-label="Active job filters">
      <span className="text-foreground-muted text-xs font-medium">Active filters</span>
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={item.onRemove}
          className="border-border bg-surface text-foreground-secondary hover:bg-surface-subtle hover:border-accent/50 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs"
          aria-label={`Remove ${item.label} filter`}
        >
          <span>{item.label}</span>
          <X className="h-3 w-3" aria-hidden="true" />
        </button>
      ))}
      {onClearAll && (
        <button
          type="button"
          onClick={onClearAll}
          className="text-foreground-muted hover:text-foreground text-xs font-medium"
        >
          Clear all
        </button>
      )}
    </fieldset>
  );
}
