import type { LucideIcon } from 'lucide-react';

interface StatisticIconProps {
  readonly icon: LucideIcon;
}

export function StatisticIcon({ icon: Icon }: StatisticIconProps) {
  return (
    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-900/30">
      <Icon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
    </div>
  );
}
