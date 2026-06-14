'use client';

import { ReactNode } from 'react';
import { AlertTriangle, Frown, CheckCircle, AlertCircle } from 'lucide-react';

interface AdminResultProps {
  readonly status: '403' | '404' | '500' | 'success' | 'info';
  readonly title: ReactNode;
  readonly subTitle?: ReactNode;
  readonly extra?: ReactNode;
}

const icons = {
  '403': AlertTriangle,
  '404': Frown,
  '500': AlertCircle,
  success: CheckCircle,
  info: AlertCircle,
};

export function AdminResult({ status, title, subTitle, extra }: AdminResultProps) {
  const Icon = icons[status];
  return (
    <div className="flex flex-col items-center justify-center px-4 py-16 text-center">
      <Icon
        className={`mb-4 h-16 w-16 ${
          status === 'success'
            ? 'text-green-600 dark:text-green-400'
            : status === 'info'
              ? 'text-blue-600 dark:text-blue-400'
              : 'text-red-600 dark:text-red-400'
        }`}
      />
      <h2 className="dark:text-md-on-surface text-2xl font-bold text-slate-900">{title}</h2>
      {subTitle && (
        <p className="dark:text-md-on-surface-variant mt-2 text-slate-600">{subTitle}</p>
      )}
      {extra && <div className="mt-6">{extra}</div>}
    </div>
  );
}
