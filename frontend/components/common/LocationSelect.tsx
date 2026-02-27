"use client";

import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useState, useRef, useEffect, useMemo } from "react";
import type { LocationItem } from "@/lib/types";

interface LocationSelectProps {
  readonly locations: LocationItem[];
  readonly selected: string[];
  readonly onChange: (selected: string[]) => void;
  readonly placeholder: string;
}

export default function LocationSelect({
  locations,
  selected,
  onChange,
  placeholder,
}: LocationSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [path, setPath] = useState<LocationItem[]>([]);
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

  useEffect(() => {
    if (!isOpen) {
      setPath([]);
      setSearch("");
    }
  }, [isOpen]);

  const currentItems = useMemo(() => {
    if (path.length === 0) return locations;
    const current = path[path.length - 1];
    return current.children || [];
  }, [path, locations]);

  const filteredItems = useMemo(() => {
    if (!search) return currentItems;
    return currentItems.filter((item) =>
      item.label.toLowerCase().includes(search.toLowerCase())
    );
  }, [currentItems, search]);

  const drillDown = (item: LocationItem) => {
    if (item.children && item.children.length > 0) {
      setPath([...path, item]);
      setSearch("");
    }
  };

  const goBack = () => {
    setPath(path.slice(0, -1));
    setSearch("");
  };

  const getBackLabel = () => {
    if (path.length === 0) return null;
    if (path.length === 1) return "Countries";
    return path[path.length - 2].label;
  };

  const toggleSelect = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((s) => s !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  const removeItem = (value: string) => {
    onChange(selected.filter((s) => s !== value));
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
    if (path.length === 0) return "Countries";
    const current = path[path.length - 1];
    return current.label;
  };

  const selectedPreview = selected.slice(0, 2);
  const hiddenSelectedCount = Math.max(0, selected.length - selectedPreview.length);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full min-h-[44px] cursor-pointer flex-wrap items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-md-outline-variant dark:bg-md-surface-container"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        {selected.length === 0 ? (
          <span className="text-slate-400 dark:text-md-on-surface">
            {placeholder}
          </span>
        ) : (
          selectedPreview.map((item) => {
            const label = getLabelForValue(locations, item) || item;
            return (
              <span
                key={item}
                className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700 dark:bg-md-surface-container-high dark:text-md-on-surface"
              >
                {label}
                <span
                  role="button"
                  tabIndex={0}
                  aria-label={`Remove ${label}`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    removeItem(item);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      e.stopPropagation();
                      removeItem(item);
                    }
                  }}
                  className="cursor-pointer hover:text-slate-900 dark:hover:text-slate-100"
                >
                  <X size={12} />
                </span>
              </span>
            );
          })
        )}
        {hiddenSelectedCount > 0 && (
          <span className="inline-flex items-center rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700 dark:bg-md-surface-container-high dark:text-md-on-surface">
            +{hiddenSelectedCount} more
          </span>
        )}
        <ChevronRight
          size={16}
          className={`ml-auto text-slate-400 transition-transform ${isOpen ? "rotate-90" : ""}`}
        />
      </button>

      {isOpen && (
        <div className="absolute z-40 mt-1 w-full rounded-lg border border-slate-300 bg-white shadow-lg dark:border-md-outline-variant dark:bg-md-surface-container">
          <div className="p-2 border-b border-slate-200 dark:border-md-outline-variant">
            {path.length > 0 && (
              <button
                onClick={goBack}
                className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 dark:text-md-on-surface-variant dark:hover:text-md-on-surface mb-2"
              >
                <ChevronLeft size={16} />
                <span>Back to {getBackLabel()}</span>
              </button>
            )}
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500 dark:text-md-on-surface-variant uppercase tracking-wide">
                {getCurrentLevelLabel()}
              </span>
              <span className="text-xs text-slate-400 dark:text-md-on-surface-variant">
                {filteredItems.length} items
              </span>
            </div>
          </div>

          <div className="p-2">
            <input
              type="text"
              placeholder={`Search ${getCurrentLevelLabel().toLowerCase()}...`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus:border-md-primary focus:outline-none dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface"
              onClick={(e) => e.stopPropagation()}
            />
          </div>

          <div className="max-h-60 overflow-y-auto">
            {filteredItems.length === 0 ? (
              <div className="px-3 py-2 text-sm text-slate-400">
                No locations found
              </div>
            ) : (
              filteredItems.map((item) => {
                const hasChildren = item.children && item.children.length > 0;
                const isSelected = selected.includes(item.value);

                return (
                  <div
                    key={item.value}
                    className="flex items-center justify-between px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-md-surface-container-high"
                  >
                    <button
                      type="button"
                      className="flex flex-1 items-center gap-2 text-left"
                      onClick={() => {
                        if (hasChildren) {
                          drillDown(item);
                        } else {
                          toggleSelect(item.value);
                        }
                      }}
                    >
                      {hasChildren && (
                        <ChevronRight size={14} className="text-slate-400" />
                      )}
                      {!hasChildren && <span className="w-3.5" />}
                      <span className="text-slate-900 dark:text-md-on-surface">
                        {item.label}
                      </span>
                      <span className="text-slate-400 dark:text-md-on-surface-variant text-xs">
                        ({item.count})
                      </span>
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSelect(item.value);
                      }}
                      aria-label={`${isSelected ? "Deselect" : "Select"} ${item.label}`}
                      className={`h-5 w-5 rounded border-2 flex items-center justify-center transition-colors ${
                        isSelected
                          ? "border-md-primary bg-md-primary"
                          : "border-slate-300 dark:border-md-outline-variant hover:border-md-primary"
                      }`}
                    >
                      {isSelected && (
                        <div className="h-2 w-2 rounded-sm bg-white" />
                      )}
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
