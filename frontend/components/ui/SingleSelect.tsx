'use client';

import { useId, useRef, useState } from 'react';
import { ChevronDown, Check } from 'lucide-react';
import {
  SelectFooter,
  SelectList,
  SelectOption,
  SelectPopoverPanel,
  SelectTrigger,
  selectClearButtonClass,
  selectDoneButtonClass,
  useSelectPopover,
} from './SelectPopover';

interface SingleSelectProps {
  readonly options: { value: string; label: string }[];
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly placeholder: string;
  readonly ariaLabel?: string;
}

export function SingleSelect({
  options,
  value,
  onChange,
  placeholder,
  ariaLabel,
}: SingleSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const firstOptionRef = useRef<HTMLButtonElement>(null);
  const listboxId = useId();
  const ref = useSelectPopover({
    isOpen,
    onOpenChange: setIsOpen,
    initialFocusRef: firstOptionRef,
    triggerRef,
  });

  const selectedOption = options.find((opt) => opt.value === value);

  return (
    <div ref={ref} className="relative">
      <SelectTrigger
        ref={triggerRef}
        onClick={() => setIsOpen(!isOpen)}
        className="cursor-pointer justify-between"
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-controls={listboxId}
        aria-label={ariaLabel}
      >
        <span className={selectedOption ? 'text-foreground' : 'text-foreground-muted'}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown
          size={16}
          className={`text-foreground-muted ml-2 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </SelectTrigger>

      {isOpen && (
        <SelectPopoverPanel>
          <SelectList id={listboxId} className="max-h-52" role="menu">
            <SelectOption
              ref={firstOptionRef}
              selected={!value}
              onClick={() => {
                onChange('');
              }}
            >
              <span className="text-foreground">{placeholder}</span>
              {!value && <Check size={16} className="text-accent" />}
            </SelectOption>
            {options.map((option) => (
              <SelectOption
                key={option.value}
                selected={value === option.value}
                onClick={() => {
                  onChange(option.value);
                }}
              >
                <span className="text-foreground">{option.label}</span>
                {value === option.value && <Check size={16} className="text-accent" />}
              </SelectOption>
            ))}
          </SelectList>
          <SelectFooter>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onChange('');
              }}
              disabled={!value}
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
