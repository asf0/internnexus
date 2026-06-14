'use client';

import { ReactNode, useEffect, useRef, useState, isValidElement, cloneElement } from 'react';
import type { LucideIcon } from 'lucide-react';

export interface AdminDropdownItem {
  readonly key: string;
  readonly label: ReactNode;
  readonly icon?: LucideIcon;
  readonly disabled?: boolean;
  readonly onClick?: () => void;
}

interface AdminDropdownProps {
  readonly trigger: ReactNode;
  readonly items: AdminDropdownItem[];
}

export function AdminDropdown({ trigger, items }: AdminDropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggle = () => setOpen((prev) => !prev);
  const triggerElement = isValidElement(trigger) ? (
    cloneElement(trigger as React.ReactElement<{ onClick?: () => void }>, { onClick: toggle })
  ) : (
    <button type="button" onClick={toggle}>
      {trigger}
    </button>
  );

  return (
    <div ref={ref} className="relative">
      {triggerElement}
      {open && (
        <div className="dark:border-md-outline-variant dark:bg-md-surface-container absolute right-0 z-50 mt-2 w-56 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg">
          <ul role="menu" aria-label="User menu">
            {items.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.key} role="none">
                  <button
                    type="button"
                    role="menuitem"
                    disabled={item.disabled}
                    onClick={() => {
                      item.onClick?.();
                      setOpen(false);
                    }}
                    className={`flex w-full items-center gap-2 px-4 py-2 text-left text-sm transition-colors ${
                      item.disabled
                        ? 'dark:text-md-on-surface-variant/50 cursor-not-allowed text-slate-400'
                        : 'dark:text-md-on-surface dark:hover:bg-md-surface-container-high text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    {Icon && <Icon className="h-4 w-4" />}
                    {item.label}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
