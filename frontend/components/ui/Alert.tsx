import { ReactNode } from 'react';
import { CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';

interface AlertProps {
  readonly type: 'success' | 'error' | 'warning' | 'info';
  readonly children: ReactNode;
  readonly className?: string;
}

const alertStyles = {
  success: {
    container:
      'bg-green-50 text-green-700 border-green-200 dark:bg-success/15 dark:text-success dark:border-success/40',
    icon: CheckCircle,
  },
  error: {
    container:
      'bg-red-50 text-red-700 border-red-200 dark:bg-surface-inset dark:text-danger dark:border-danger/40',
    icon: AlertCircle,
  },
  warning: {
    container:
      'bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-warning/15 dark:text-warning dark:border-warning/40',
    icon: AlertTriangle,
  },
  info: {
    container:
      'bg-blue-50 text-blue-700 border-blue-200 dark:bg-accent/15 dark:text-accent dark:border-accent/40',
    icon: Info,
  },
};

export function Alert({ type, children, className = '' }: AlertProps) {
  const { container, icon: Icon } = alertStyles[type];

  return (
    <div className={`flex items-start gap-3 rounded-lg border p-4 ${container} ${className}`}>
      <Icon className="mt-0.5 h-5 w-5 flex-shrink-0" />
      <div className="flex-1">{children}</div>
    </div>
  );
}
