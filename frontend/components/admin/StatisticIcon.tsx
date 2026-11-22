import type { LucideIcon } from 'lucide-react';

interface StatisticIconProps {
  readonly icon: LucideIcon;
}

export function StatisticIcon({ icon: Icon }: StatisticIconProps) {
  return (
    <div className="bg-accent/15 flex h-12 w-12 items-center justify-center rounded-lg">
      <Icon className="text-accent h-6 w-6" />
    </div>
  );
}
