'use client';

import { Check, ChevronDown } from 'lucide-react';
import { useId, useMemo, useRef, useState } from 'react';
import {
  SelectEmpty,
  SelectFooter,
  SelectList,
  SelectOption,
  SelectPopoverPanel,
  SelectSearchInput,
  SelectTrigger,
  selectClearButtonClass,
  selectDoneButtonClass,
  useSelectPopover,
} from '@/components/ui/SelectPopover';

interface MultiSelectProps {
  readonly options: string[];
  readonly selected: string[];
  readonly onChange: (selected: string[]) => void;
  readonly placeholder: string;
  readonly labelMap?: Record<string, string>;
  readonly disabled?: boolean;
  readonly loading?: boolean;
}

export default function MultiSelect({
  options,
  selected,
  onChange,
  placeholder,
  labelMap,
  disabled = false,
  loading = false,
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const triggerRef = useRef<HTMLButtonElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listboxId = useId();
  const ref = useSelectPopover({
    isOpen,
    onOpenChange: setIsOpen,
    initialFocusRef: searchInputRef,
    triggerRef,
  });

  const getLabel = (option: string) => labelMap?.[option] || option;

  const filteredOptions = useMemo(() => {
    const matching = options.filter((option) =>
      getLabel(option).toLowerCase().includes(search.toLowerCase())
    );

    return matching.sort((a, b) => {
      const aSelected = selected.includes(a);
      const bSelected = selected.includes(b);
      if (aSelected !== bSelected) {
        return aSelected ? -1 : 1;
      }
      return getLabel(a).localeCompare(getLabel(b));
    });
  }, [options, search, selected]);

  const selectedPreview = selected.slice(0, 2);
  const hiddenSelectedCount = Math.max(0, selected.length - selectedPreview.length);

  const toggleOption = (option: string) => {
    if (selected.includes(option)) {
      onChange(selected.filter((item) => item !== option));
    } else {
      onChange([...selected, option]);
    }
  };

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
          selectedPreview.map((item) => (
            <span
              key={item}
              className="bg-surface-subtle text-foreground-secondary inline-flex items-center rounded px-2 py-0.5 text-xs"
            >
              {getLabel(item)}
            </span>
          ))
        )}
        {hiddenSelectedCount > 0 && (
          <span className="bg-surface-subtle text-foreground-secondary inline-flex items-center rounded px-2 py-0.5 text-xs">
            +{hiddenSelectedCount} more
          </span>
        )}
        <ChevronDown
          size={16}
          className={`text-foreground-muted ml-auto transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </SelectTrigger>

      {isOpen && (
        <SelectPopoverPanel>
          <div className="p-2">
            <SelectSearchInput
              ref={searchInputRef}
              placeholder="Search..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          <SelectList id={listboxId} className="max-h-52" role="menu" aria-label={placeholder}>
            {filteredOptions.length === 0 ? (
              <SelectEmpty>{loading ? 'Loading...' : 'No results found'}</SelectEmpty>
            ) : (
              filteredOptions.map((option) => (
                <SelectOption
                  key={option}
                  selected={selected.includes(option)}
                  selectionMode="multiple"
                  onClick={() => toggleOption(option)}
                >
                  <span>{getLabel(option)}</span>
                  {selected.includes(option) && <Check size={16} className="text-accent" />}
                </SelectOption>
              ))
            )}
          </SelectList>
          <SelectFooter>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onChange([]);
              }}
              disabled={selected.length === 0}
              className={selectClearButtonClass}
            >
              Clear
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setIsOpen(false);
              }}
              className={selectDoneButtonClass}
            >
              Done
            </button>
          </SelectFooter>
        </SelectPopoverPanel>
      )}
    </div>
  );
}
