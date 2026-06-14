'use client';

import { ReactNode } from 'react';

interface AdminStatisticProps {
  readonly title: ReactNode;
  readonly value: number | string;
  readonly precision?: number;
  readonly className?: string;
  readonly valueClassName?: string;
}

export function AdminStatistic({
  title,
  value,
  precision,
  className = '',
  valueClassName = '',
}: AdminStatisticProps) {
  const formattedValue =
    typeof value === 'number' && precision !== undefined
      ? value.toLocaleString('en-US', {
          minimumFractionDigits: precision,
          maximumFractionDigits: precision,
        })
      : typeof value === 'number'
        ? value.toLocaleString('en-US')
        : value;

  return (
    <div className={className}>
      <div className="dark:text-md-on-surface-variant text-sm text-slate-500">{title}</div>
      <div
        className={`dark:text-md-on-surface mt-1 text-2xl font-semibold text-slate-900 ${valueClassName}`}
      >
        {formattedValue}
      </div>
    </div>
  );
}
