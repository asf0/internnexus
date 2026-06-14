import { ReactNode } from 'react';

interface AdminCardProps {
  readonly children: ReactNode;
  readonly title?: ReactNode;
  readonly extra?: ReactNode;
  readonly className?: string;
}

export function AdminCard({ children, title, extra, className = '' }: AdminCardProps) {
  return (
    <div
      className={`dark:border-md-outline-variant dark:bg-md-surface-container rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}
    >
      {(title || extra) && (
        <div className="dark:border-md-outline-variant flex items-center justify-between border-b border-slate-200 px-6 py-4">
          {title && (
            <h3 className="dark:text-md-on-surface text-base font-semibold text-slate-900">
              {title}
            </h3>
          )}
          {extra && <div>{extra}</div>}
        </div>
      )}
      <div className="px-6 py-4">{children}</div>
    </div>
  );
}
