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
      'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800',
    icon: CheckCircle,
  },
  error: {
    container:
      'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800',
    icon: AlertCircle,
  },
  warning: {
    container:
      'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800',
    icon: AlertTriangle,
  },
  info: {
    container:
      'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800',
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
