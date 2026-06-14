'use client';

import { ReactNode, MouseEvent, useMemo } from 'react';
import type { Key } from 'react';
import { LoadingSpinner } from '@/components/ui';
import Pagination from '@/components/ui/Pagination';

export interface AdminColumn<T> {
  readonly title: ReactNode;
  readonly dataIndex?: keyof T | string;
  readonly key?: string;
  readonly width?: number | string;
  readonly align?: 'left' | 'center' | 'right';
  readonly ellipsis?: boolean;
  readonly fixed?: 'left' | 'right';
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  readonly render?: (value: any, record: T, index: number) => ReactNode;
}

export interface AdminPagination {
  readonly current?: number;
  readonly pageSize?: number;
  readonly total?: number;
  readonly buildPageUrl?: (page: number) => string;
  readonly onChange?: (page: number) => void;
  readonly showSizeChanger?: boolean;
  readonly showTotal?: (total: number, range: [number, number]) => string;
}

export interface AdminRowSelection {
  readonly selectedRowKeys: Key[];
  readonly onChange: (keys: Key[]) => void;
}

interface AdminTableProps<T> {
  readonly dataSource: readonly T[];
  readonly columns: readonly AdminColumn<T>[];
  readonly rowKey: keyof T | ((record: T) => Key);
  readonly pagination?: AdminPagination | false;
  readonly rowSelection?: AdminRowSelection;
  readonly loading?: boolean;
  readonly emptyText?: ReactNode;
  readonly size?: 'small' | 'middle';
  readonly scroll?: { x?: number | string; y?: number | string };
  readonly className?: string;
  readonly onRow?: (
    record: T,
    index: number
  ) => { onClick?: () => void; style?: React.CSSProperties; className?: string };
}

function getRowKey<T>(record: T, rowKey: keyof T | ((record: T) => Key)): Key {
  if (typeof rowKey === 'function') return rowKey(record);
  const value = (record as Record<string, unknown>)[rowKey as string];
  return String(value ?? '');
}

function getCellValue<T>(record: T, dataIndex?: keyof T | string): unknown {
  if (!dataIndex) return undefined;
  return (record as Record<string, unknown>)[dataIndex as string];
}

function alignClass(align?: 'left' | 'center' | 'right'): string {
  switch (align) {
    case 'center':
      return 'text-center';
    case 'right':
      return 'text-right';
    default:
      return 'text-left';
  }
}

export function AdminTable<T>({
  dataSource,
  columns,
  rowKey,
  pagination,
  rowSelection,
  loading,
  emptyText,
  size = 'middle',
  scroll,
  className = '',
  onRow,
}: AdminTableProps<T>) {
  const currentPage = pagination ? pagination.current || 1 : 1;
  const pageSize = pagination ? pagination.pageSize || 20 : 20;
  const total = pagination ? pagination.total || 0 : 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const allKeys = useMemo(
    () => dataSource.map((row) => getRowKey(row, rowKey)),
    [dataSource, rowKey]
  );
  const allSelected =
    dataSource.length > 0 && allKeys.every((k) => rowSelection?.selectedRowKeys.includes(k));

  const handleToggleAll = () => {
    if (!rowSelection) return;
    if (allSelected) {
      const pageKeys = new Set(allKeys);
      rowSelection.onChange(rowSelection.selectedRowKeys.filter((k) => !pageKeys.has(k)));
    } else {
      const combined = Array.from(new Set([...rowSelection.selectedRowKeys, ...allKeys]));
      rowSelection.onChange(combined);
    }
  };

  const handleToggleRow = (key: Key) => {
    if (!rowSelection) return;
    if (rowSelection.selectedRowKeys.includes(key)) {
      rowSelection.onChange(rowSelection.selectedRowKeys.filter((k) => k !== key));
    } else {
      rowSelection.onChange([...rowSelection.selectedRowKeys, key]);
    }
  };

  const wrapperStyle: React.CSSProperties = {};
  if (scroll?.x) wrapperStyle.minWidth = typeof scroll.x === 'number' ? scroll.x : scroll.x;

  const bodyStyle: React.CSSProperties = {};
  if (scroll?.y) bodyStyle.maxHeight = typeof scroll.y === 'number' ? scroll.y : scroll.y;

  const cellPadding = size === 'small' ? 'px-3 py-2' : 'px-4 py-3';

  return (
    <div className={`relative ${className}`}>
      <div className="dark:border-md-outline-variant w-full overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full border-collapse text-sm" style={wrapperStyle}>
          <thead className="dark:bg-md-surface-container-high bg-slate-100">
            <tr>
              {rowSelection && (
                <th className={`${cellPadding} w-12 text-left`}>
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={handleToggleAll}
                    aria-label="Select all rows"
                    className="dark:border-md-outline-variant dark:bg-md-surface-container h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                </th>
              )}
              {columns.map((col) => (
                <th
                  key={String(col.key ?? col.dataIndex ?? col.title)}
                  className={`${cellPadding} dark:text-md-on-surface-variant font-semibold text-slate-700 ${alignClass(col.align)}`}
                  style={{ width: col.width, minWidth: col.width }}
                >
                  {col.title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataSource.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length + (rowSelection ? 1 : 0)}
                  className="dark:text-md-on-surface-variant px-4 py-8 text-center text-slate-500"
                >
                  {emptyText ?? 'No data'}
                </td>
              </tr>
            ) : (
              dataSource.map((row, index) => {
                const key = getRowKey(row, rowKey);
                const rowProps = onRow?.(row, index) ?? {};
                return (
                  <tr
                    key={key}
                    className={`dark:border-md-outline-variant dark:hover:bg-md-surface-container-high border-t border-slate-200 transition-colors hover:bg-slate-50 ${rowProps.className ?? ''}`}
                    style={rowProps.style}
                    onClick={rowProps.onClick}
                  >
                    {rowSelection && (
                      <td className={cellPadding} onClick={(e: MouseEvent) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={rowSelection.selectedRowKeys.includes(key)}
                          onChange={() => handleToggleRow(key)}
                          aria-label="Select row"
                          className="dark:border-md-outline-variant dark:bg-md-surface-container h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        />
                      </td>
                    )}
                    {columns.map((col) => {
                      const value = getCellValue(row, col.dataIndex);
                      const content = col.render ? col.render(value, row, index) : value;
                      return (
                        <td
                          key={String(col.key ?? col.dataIndex ?? col.title)}
                          className={`${cellPadding} ${alignClass(col.align)} ${col.ellipsis ? 'max-w-[1px] overflow-hidden text-ellipsis whitespace-nowrap' : ''}`}
                          style={{ width: col.width, minWidth: col.width }}
                        >
                          {content as ReactNode}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {pagination && (
        <div className="mt-4">
          {pagination.buildPageUrl ? (
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              buildPageUrl={pagination.buildPageUrl}
              totalItems={total}
              pageSize={pageSize}
            />
          ) : (
            <div className="flex items-center justify-between">
              <button
                type="button"
                disabled={currentPage <= 1}
                onClick={() => pagination.onChange?.(currentPage - 1)}
                className="dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <span className="dark:text-md-on-surface-variant text-sm text-slate-500">
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => pagination.onChange?.(currentPage + 1)}
                className="dark:border-md-outline-variant dark:bg-md-surface-container dark:text-md-on-surface-variant dark:hover:bg-md-surface-container-high rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-white/70 backdrop-blur-sm dark:bg-black/50">
          <LoadingSpinner size="lg" />
        </div>
      )}
    </div>
  );
}
