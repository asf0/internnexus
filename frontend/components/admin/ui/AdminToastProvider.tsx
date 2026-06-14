'use client';

import { ReactNode, createContext, useCallback, useContext, useState } from 'react';
import { Toast } from '@/components/ui';

interface ToastMessage {
  readonly id: string;
  readonly message: string;
  readonly type: 'success' | 'error' | 'warning' | 'info';
}

interface AdminMessageApi {
  readonly success: (message: string) => void;
  readonly error: (message: string) => void;
  readonly warning: (message: string) => void;
  readonly info: (message: string) => void;
}

const AdminToastContext = createContext<AdminMessageApi | null>(null);

let nextId = 1;

export function AdminToastProvider({ children }: { readonly children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (message: string, type: ToastMessage['type']) => {
      const id = String(nextId++);
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => removeToast(id), 4000);
    },
    [removeToast]
  );

  const api: AdminMessageApi = {
    success: (message) => addToast(message, 'success'),
    error: (message) => addToast(message, 'error'),
    warning: (message) => addToast(message, 'warning'),
    info: (message) => addToast(message, 'info'),
  };

  return (
    <AdminToastContext.Provider value={api}>
      {children}
      <div className="fixed right-4 bottom-4 z-[120] flex flex-col gap-2">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </AdminToastContext.Provider>
  );
}

export function useAdminMessage(): AdminMessageApi {
  const ctx = useContext(AdminToastContext);
  if (!ctx) {
    throw new Error('useAdminMessage must be used within AdminToastProvider');
  }
  return ctx;
}
