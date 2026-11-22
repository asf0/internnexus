'use client';

import { ReactNode } from 'react';

interface AdminStatisticProps {
  readonly title: ReactNode;
  readonly value: number | string;
  readonly precision?: number;
  readonly className?: string;
  readonly valueClassName?: string;
}

function formatStatistic(value: number | string, precision?: number): string {
  if (typeof value !== 'number') return value;
  if (precision === undefined) return value.toLocaleString('en-US');
  return value.toLocaleString('en-US', {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  });
}

export function AdminStatistic({
  title,
  value,
  precision,
  className = '',
  valueClassName = '',
}: AdminStatisticProps) {
  const formattedValue = formatStatistic(value, precision);

  return (
    <div className={className}>
      <div className="text-foreground-muted text-sm">{title}</div>
      <div className={`text-foreground mt-1 text-2xl font-semibold ${valueClassName}`}>
        {formattedValue}
      </div>
    </div>
  );
}
