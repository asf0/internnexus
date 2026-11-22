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

const iconColors: Record<AdminResultProps['status'], string> = {
  '403': 'text-danger',
  '404': 'text-danger',
  '500': 'text-danger',
  success: 'text-success',
  info: 'text-accent',
};

export function AdminResult({ status, title, subTitle, extra }: AdminResultProps) {
  const Icon = icons[status];
  return (
    <div className="flex flex-col items-center justify-center px-4 py-16 text-center">
      <Icon className={`mb-4 h-16 w-16 ${iconColors[status]}`} />
      <h2 className="text-foreground text-2xl font-bold">{title}</h2>
      {subTitle && <p className="text-foreground-muted mt-2">{subTitle}</p>}
      {extra && <div className="mt-6">{extra}</div>}
    </div>
  );
}
