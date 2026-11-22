'use client';

import { Check, ChevronLeft, ChevronRight } from 'lucide-react';
import { useEffect, useId, useMemo, useRef, useState } from 'react';
import type { LocationItem } from '@/lib/types';
import {
  SelectEmpty,
  SelectList,
  SelectOptionRow,
  SelectPopoverPanel,
  SelectSearchInput,
  SelectTrigger,
  useSelectPopover,
} from '@/components/ui/SelectPopover';

interface LocationSelectProps {
  readonly locations: LocationItem[];
  readonly selected: string[];
  readonly onChange: (selected: string[]) => void;
  readonly placeholder: string;
  readonly disabled?: boolean;
}

export default function LocationSelect({
  locations,
  selected,
  onChange,
  placeholder,
  disabled = false,
}: LocationSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [path, setPath] = useState<LocationItem[]>([]);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listboxId = useId();
  const ref = useSelectPopover({
    isOpen,
    onOpenChange: setIsOpen,
    initialFocusRef: searchInputRef,
    triggerRef,
  });

  useEffect(() => {
    if (isOpen) return;
    setPath([]);
    setSearch('');
  }, [isOpen]);

  const currentItems = useMemo(() => {
    if (path.length === 0) return locations;
    const current = path.at(-1)!;
    return current.children || [];
  }, [path, locations]);

  const filteredItems = useMemo(() => {
    if (!search) return currentItems;
    return currentItems.filter((item) => item.label.toLowerCase().includes(search.toLowerCase()));
  }, [currentItems, search]);

  const drillDown = (item: LocationItem) => {
    if (item.children && item.children.length > 0) {
      setPath([...path, item]);
      setSearch('');
    }
  };

  const goBack = () => {
    setPath(path.slice(0, -1));
    setSearch('');
  };

  const getBackLabel = () => {
    if (path.length === 0) return null;
    if (path.length === 1) return 'Countries';
    return path.at(-2)!.label;
  };

  const toggleSelect = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((s) => s !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  const getLabelForValue = (items: LocationItem[], value: string): string | null => {
    for (const item of items) {
      if (item.value === value) return item.label;
      if (item.children) {
        const found = getLabelForValue(item.children, value);
        if (found) return found;
      }
    }
    return null;
  };

  const getCurrentLevelLabel = () => {
    if (path.length === 0) return 'Countries';
    const current = path.at(-1)!;
    return current.label;
  };

  const selectedPreview = selected.slice(0, 2);
  const hiddenSelectedCount = Math.max(0, selected.length - selectedPreview.length);

  return (
    <div ref={ref} className="relative">
      <SelectTrigger
        ref={triggerRef}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className="flex-wrap gap-1 disabled:cursor-not-allowed"
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-controls={listboxId}
        aria-label={placeholder}
      >
        {selected.length === 0 ? (
          <span className="text-foreground-muted">{placeholder}</span>
        ) : (
          selectedPreview.map((item) => {
            const label = getLabelForValue(locations, item) || item;
            return (
              <span
                key={item}
                className="bg-surface-subtle text-foreground-secondary inline-flex items-center rounded px-2 py-0.5 text-xs"
              >
                {label}
              </span>
            );
          })
        )}
        {hiddenSelectedCount > 0 && (
          <span className="bg-surface-subtle text-foreground-secondary inline-flex items-center rounded px-2 py-0.5 text-xs">
            +{hiddenSelectedCount} more
          </span>
        )}
        <ChevronRight
          size={16}
          className={`text-foreground-muted ml-auto transition-transform ${isOpen ? 'rotate-90' : ''}`}
        />
      </SelectTrigger>

      {isOpen && (
        <SelectPopoverPanel>
          <div className="border-border border-b p-2">
            {path.length > 0 && (
              <button
                type="button"
                onClick={goBack}
                className="text-foreground-secondary hover:text-foreground mb-2 flex items-center gap-1 text-sm"
              >
                <ChevronLeft size={16} />
                <span>Back to {getBackLabel()}</span>
              </button>
            )}
            <div className="flex items-center justify-between">
              <span className="text-foreground-secondary text-xs font-medium tracking-wide uppercase">
                {getCurrentLevelLabel()}
              </span>
              <span className="text-foreground-muted text-xs">{filteredItems.length} items</span>
            </div>
          </div>

          <div className="p-2">
            <SelectSearchInput
              ref={searchInputRef}
              placeholder={`Search ${getCurrentLevelLabel().toLowerCase()}...`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onClick={(e) => e.stopPropagation()}
            />
          </div>

          <SelectList id={listboxId} role="menu" aria-label={placeholder}>
            {filteredItems.length === 0 ? (
              <SelectEmpty>No locations found</SelectEmpty>
            ) : (
              filteredItems.map((item) => {
                const hasChildren = item.children && item.children.length > 0;
                const isSelected = selected.includes(item.value);

                return (
                  <SelectOptionRow key={item.value}>
                    <button
                      type="button"
                      role="menuitemcheckbox"
                      aria-checked={isSelected}
                      className="flex flex-1 items-center gap-2 text-left"
                      onClick={() => toggleSelect(item.value)}
                    >
                      <span
                        className={`flex h-5 w-5 items-center justify-center rounded border-2 transition-colors ${
                          isSelected ? 'border-accent bg-accent' : 'border-border'
                        }`}
                      >
                        {isSelected && <Check size={12} className="text-on-accent" />}
                      </span>
                      <span className="text-foreground">{item.label}</span>
                      <span className="text-foreground-muted text-xs">({item.count})</span>
                    </button>
                    {hasChildren && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          drillDown(item);
                        }}
                        aria-label={`Browse ${item.label}`}
                        className="text-foreground-muted hover:text-accent rounded p-1"
                      >
                        <ChevronRight size={16} />
                      </button>
                    )}
                  </SelectOptionRow>
                );
              })
            )}
          </SelectList>
        </SelectPopoverPanel>
      )}
    </div>
  );
}
