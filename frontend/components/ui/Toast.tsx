import { X } from 'lucide-react';
import { Alert } from './Alert';

interface ToastProps {
  readonly message: string;
  readonly onClose: () => void;
  readonly type?: 'success' | 'error' | 'warning' | 'info';
}

export function Toast({ message, onClose, type = 'warning' }: ToastProps) {
  const isUrgent = type === 'error' || type === 'warning';

  return (
    <div
      className="fixed right-4 bottom-4 z-[120] w-[calc(100vw-2rem)] max-w-sm shadow-xl"
      role={isUrgent ? 'alert' : 'status'}
      aria-live={isUrgent ? 'assertive' : 'polite'}
    >
      <Alert type={type} className="pr-2">
        <div className="flex items-start justify-between gap-3">
          <p className="text-sm">{message}</p>
          <button
            type="button"
            onClick={onClose}
            aria-label="Dismiss notification"
            className="rounded-md p-1 transition-colors hover:bg-black/10 dark:hover:bg-white/10"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </Alert>
    </div>
  );
}
