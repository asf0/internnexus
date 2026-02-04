"use client";

import { Check, ChevronDown, X } from "lucide-react";
import { useState, useRef, useEffect } from "react";

interface MultiSelectProps {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  placeholder: string;
  labelMap?: Record<string, string>;
}

export default function MultiSelect({ options, selected, onChange, placeholder, labelMap }: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  const getLabel = (option: string) => labelMap?.[option] || option;

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredOptions = options.filter((option) =>
    getLabel(option).toLowerCase().includes(search.toLowerCase())
  );

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
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex min-h-[38px] cursor-pointer flex-wrap items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
      >
        {selected.length === 0 ? (
          <span className="text-slate-400 dark:text-slate-500">{placeholder}</span>
        ) : (
          selected.map((item) => (
            <span
              key={item}
              className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700 dark:bg-slate-700 dark:text-slate-300"
            >
              {getLabel(item)}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeOption(item);
                }}
                className="hover:text-slate-900 dark:hover:text-slate-100"
              >
                <X size={12} />
              </button>
            </span>
          ))
        )}
        <ChevronDown
          size={16}
          className={`ml-auto text-slate-400 transition-transform ${isOpen ? "rotate-180" : ""}`}
        />
      </div>

      {isOpen && (
        <div className="absolute z-10 mt-1 w-full rounded-lg border border-slate-300 bg-white shadow-lg dark:border-slate-600 dark:bg-slate-800">
          <div className="p-2">
            <input
              type="text"
              placeholder="Search..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus:border-slate-500 focus:outline-none dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          <div className="max-h-60 overflow-y-auto">
            {filteredOptions.length === 0 ? (
              <div className="px-3 py-2 text-sm text-slate-400">No results found</div>
            ) : (
              filteredOptions.map((option) => (
                <div
                  key={option}
                  onClick={() => toggleOption(option)}
                  className="flex cursor-pointer items-center justify-between px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700"
                >
                  <span className="text-slate-900 dark:text-slate-100">{getLabel(option)}</span>
                  {selected.includes(option) && (
                    <Check size={16} className="text-slate-900 dark:text-slate-100" />
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
