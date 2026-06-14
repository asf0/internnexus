'use client';

import { ReactNode, useState } from 'react';

export interface AdminTabItem {
  readonly key: string;
  readonly label: ReactNode;
  readonly children: ReactNode;
}

interface AdminTabsProps {
  readonly items: AdminTabItem[];
  readonly defaultActiveKey?: string;
  readonly activeKey?: string;
  readonly onChange?: (key: string) => void;
}

export function AdminTabs({
  items,
  defaultActiveKey,
  activeKey: controlledKey,
  onChange,
}: AdminTabsProps) {
  const [internalKey, setInternalKey] = useState(defaultActiveKey || items[0]?.key);
  const activeKey = controlledKey !== undefined ? controlledKey : internalKey;

  const handleClick = (key: string) => {
    setInternalKey(key);
    onChange?.(key);
  };

  const activeItem = items.find((item) => item.key === activeKey) || items[0];

  return (
    <div>
      <div
        role="tablist"
        aria-label="Admin tabs"
        className="dark:border-md-outline-variant flex border-b border-slate-200"
      >
        {items.map((item) => {
          const isActive = item.key === activeKey;
          return (
            <button
              key={item.key}
              role="tab"
              aria-selected={isActive}
              type="button"
              onClick={() => handleClick(item.key)}
              className={`relative flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors focus:outline-none ${
                isActive
                  ? 'text-blue-600 dark:text-blue-400'
                  : 'dark:text-md-on-surface-variant dark:hover:text-md-on-surface text-slate-600 hover:text-slate-900'
              }`}
            >
              {item.label}
              {isActive && (
                <span className="absolute right-0 bottom-0 left-0 h-0.5 bg-blue-600 dark:bg-blue-400" />
              )}
            </button>
          );
        })}
      </div>
      <div role="tabpanel" className="mt-6">
        {activeItem?.children}
      </div>
    </div>
  );
}
