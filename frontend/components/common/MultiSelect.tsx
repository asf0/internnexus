'use client';

import { Check, ChevronDown, X } from 'lucide-react';
import { useState, useRef, useEffect, useMemo } from 'react';

interface MultiSelectProps {
  readonly options: string[];
  readonly selected: string[];
  readonly onChange: (selected: string[]) => void;
  readonly placeholder: string;
  readonly labelMap?: Record<string, string>;
  readonly disabled?: boolean;
}

export default function MultiSelect({
  options,
  selected,
  onChange,
  placeholder,
  labelMap,
  disabled = false,
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  const getLabel = (option: string) => labelMap?.[option] || option;

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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

  const removeOption = (option: string) => {
    onChange(selected.filter((item) => item !== option));
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`dark:border-md-outline-variant dark:bg-md-surface-container flex min-h-[44px] w-full flex-wrap items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm ${
          disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
        }`}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label={placeholder}
      >
        {selected.length === 0 ? (
          <span className="dark:text-md-on-surface text-slate-400">{placeholder}</span>
        ) : (
          selectedPreview.map((item) => (
            <span
              key={item}
              className="dark:bg-md-surface-container-high dark:text-md-on-surface inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700"
            >
              {getLabel(item)}
              <span
                role="button"
                tabIndex={0}
                aria-label={`Remove ${getLabel(item)}`}
                onMouseDown={(e) => {
                  e.preventDefault();
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  removeOption(item);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    e.stopPropagation();
                    removeOption(item);
                  }
                }}
                className="cursor-pointer hover:text-slate-900 dark:hover:text-slate-100"
              >
                <X size={12} />
              </span>
            </span>
          ))
        )}
        {hiddenSelectedCount > 0 && (
          <span className="dark:bg-md-surface-container-high dark:text-md-on-surface inline-flex items-center rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
            +{hiddenSelectedCount} more
          </span>
        )}
        <ChevronDown
          size={16}
          className={`ml-auto text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {isOpen && (
        <div className="dark:border-md-outline-variant dark:bg-md-surface-container absolute z-40 mt-1 w-full overflow-hidden rounded-lg border border-slate-300 bg-white shadow-lg">
          <div className="p-2">
            <input
              type="text"
              placeholder="Search..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="focus:border-md-primary dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface w-full rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus:outline-none"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          <div
            className="max-h-52 overflow-y-auto"
            role="listbox"
            aria-multiselectable="true"
            aria-label={placeholder}
          >
            {filteredOptions.length === 0 ? (
              <div className="px-3 py-2 text-sm text-slate-400">No results found</div>
            ) : (
              filteredOptions.map((option) => (
                <button
                  type="button"
                  key={option}
                  role="option"
                  aria-selected={selected.includes(option)}
                  onClick={() => toggleOption(option)}
                  className="dark:hover:bg-md-surface-container-high flex w-full cursor-pointer items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-50"
                >
                  <span className="dark:text-md-on-surface text-slate-900">{getLabel(option)}</span>
                  {selected.includes(option) && (
                    <Check size={16} className="dark:text-md-on-surface text-slate-900" />
                  )}
                </button>
              ))
            )}
          </div>
          <div className="dark:border-md-outline-variant dark:bg-md-surface-container flex items-center justify-between border-t border-slate-200 bg-white p-2">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onChange([]);
              }}
              disabled={selected.length === 0}
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
