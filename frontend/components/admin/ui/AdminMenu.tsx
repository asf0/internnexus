'use client';

import { LucideIcon } from 'lucide-react';
import Link from 'next/link';

export interface AdminMenuItem {
  readonly key: string;
  readonly icon: LucideIcon;
  readonly label: string;
}

interface AdminMenuProps {
  readonly items: AdminMenuItem[];
  readonly selectedKey: string;
}

export function AdminMenu({ items, selectedKey }: AdminMenuProps) {
  return (
    <nav aria-label="Admin navigation">
      <ul className="space-y-1 px-3 py-4">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = item.key === selectedKey;
          return (
            <li key={item.key}>
              <Link
                href={item.key}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600/10 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400'
                    : 'dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high dark:hover:text-md-on-surface text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
