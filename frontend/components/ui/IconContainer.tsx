import { LucideIcon } from 'lucide-react';

interface IconContainerProps {
  readonly icon: LucideIcon;
  readonly color: 'blue' | 'purple' | 'green' | 'red';
  readonly className?: string;
}

export function IconContainer({ icon: Icon, color, className = '' }: IconContainerProps) {
  const colors = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-accent/15 dark:text-accent',
    purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
    green: 'bg-green-100 text-green-600 dark:bg-success/15 dark:text-success',
    red: 'bg-red-100 text-red-600 dark:bg-danger/15 dark:text-danger',
  };

  return (
    <div className={`rounded-lg p-2 ${colors[color]} ${className}`}>
      <Icon className="h-6 w-6" />
    </div>
  );
}
