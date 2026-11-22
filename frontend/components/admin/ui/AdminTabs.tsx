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
  const activeKey = controlledKey ?? internalKey;

  const handleClick = (key: string) => {
    setInternalKey(key);
    onChange?.(key);
  };

  const activeItem = items.find((item) => item.key === activeKey) || items[0];

  return (
    <div>
      <div role="tablist" aria-label="Admin tabs" className="border-border flex border-b">
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
                isActive ? 'text-accent' : 'text-foreground-muted hover:text-foreground'
              }`}
            >
              {item.label}
              {isActive && <span className="bg-accent absolute right-0 bottom-0 left-0 h-0.5" />}
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
