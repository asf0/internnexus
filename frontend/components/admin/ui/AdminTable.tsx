'use client';

import { Fragment, ReactNode, useMemo, useState, useSyncExternalStore } from 'react';
import type { Key } from 'react';
import { ChevronDown } from 'lucide-react';
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
  /** Controls how much space a column receives at responsive breakpoints. */
  readonly priority?: 'primary' | 'secondary' | 'detail';
  /** A shorter, plain-language label for stacked and expanded row details. */
  readonly mobileLabel?: ReactNode;
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
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'bigint') {
    return value;
  }
  return '';
}

function getCellValue<T>(record: T, dataIndex?: keyof T | string): unknown {
  if (!dataIndex) return undefined;
  return (record as Record<string, unknown>)[dataIndex as string];
}

function getColumnKey<T>(column: AdminColumn<T>, index: number): string {
  return String(column.key ?? column.dataIndex ?? index);
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

type TableViewport = 'mobile' | 'tablet' | 'desktop';

function getTableViewport(): TableViewport {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return 'desktop';
  if (window.matchMedia('(min-width: 1200px)').matches) return 'desktop';
  if (window.matchMedia('(min-width: 768px)').matches) return 'tablet';
  return 'mobile';
}

function subscribeToTableViewport(onChange: () => void): () => void {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return () => {};
  const tabletQuery = window.matchMedia('(min-width: 768px)');
  const desktopQuery = window.matchMedia('(min-width: 1200px)');
  tabletQuery.addEventListener('change', onChange);
  desktopQuery.addEventListener('change', onChange);
  return () => {
    tabletQuery.removeEventListener('change', onChange);
    desktopQuery.removeEventListener('change', onChange);
  };
}

function toggleAllRows(
  selection: AdminRowSelection | undefined,
  allKeys: Key[],
  allSelected: boolean
) {
  if (!selection) return;
  if (allSelected) {
    const pageKeys = new Set(allKeys);
    selection.onChange(selection.selectedRowKeys.filter((key) => !pageKeys.has(key)));
    return;
  }
  selection.onChange(Array.from(new Set([...selection.selectedRowKeys, ...allKeys])));
}

function toggleRow(selection: AdminRowSelection | undefined, key: Key) {
  if (!selection) return;
  const selected = selection.selectedRowKeys;
  selection.onChange(
    selected.includes(key) ? selected.filter((item) => item !== key) : [...selected, key]
  );
}

function toggleKey(current: Set<Key>, key: Key): Set<Key> {
  const next = new Set(current);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  return next;
}

const paginationButtonClass =
  'border-border bg-surface text-foreground-secondary hover:bg-surface-subtle rounded-lg border px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50';

function AdminTablePagination({ pagination }: { readonly pagination?: AdminPagination | false }) {
  if (!pagination) return null;
  const currentPage = pagination.current || 1;
  const pageSize = pagination.pageSize || 20;
  const total = pagination.total || 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  if (pagination.buildPageUrl) {
    return (
      <div className="mt-4">
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          buildPageUrl={pagination.buildPageUrl}
          totalItems={total}
          pageSize={pageSize}
        />
      </div>
    );
  }

  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
      <button
        type="button"
        disabled={currentPage <= 1}
        onClick={() => pagination.onChange?.(currentPage - 1)}
        className={paginationButtonClass}
      >
        Previous
      </button>
      <span className="text-foreground-muted text-sm">
        Page {currentPage} of {totalPages}
      </span>
      <button
        type="button"
        disabled={currentPage >= totalPages}
        onClick={() => pagination.onChange?.(currentPage + 1)}
        className={paginationButtonClass}
      >
        Next
      </button>
    </div>
  );
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
  const [expandedRowKeys, setExpandedRowKeys] = useState<Set<Key>>(() => new Set());
  const viewport = useSyncExternalStore(
    subscribeToTableViewport,
    getTableViewport,
    () => 'desktop'
  );

  const allKeys = useMemo(
    () => dataSource.map((row) => getRowKey(row, rowKey)),
    [dataSource, rowKey]
  );
  const allSelected =
    dataSource.length > 0 && allKeys.every((k) => rowSelection?.selectedRowKeys.includes(k));

  const handleToggleAll = () => toggleAllRows(rowSelection, allKeys, allSelected);
  const handleToggleRow = (key: Key) => toggleRow(rowSelection, key);

  const bodyStyle: React.CSSProperties = {};
  if (scroll?.y) bodyStyle.maxHeight = scroll.y;

  const cellPadding = size === 'small' ? 'px-3 py-2' : 'px-4 py-3';
  const checkboxClass = 'border-border bg-surface text-accent focus:ring-accent h-4 w-4 rounded';

  const primaryColumns = columns.filter((column, index) =>
    column.priority ? column.priority === 'primary' : index === 0
  );
  const tabletColumns = columns.filter((column) => column.priority !== 'detail');
  const detailColumns = columns.filter((column) => column.priority === 'detail');

  const renderCell = (column: AdminColumn<T>, row: T, index: number) => {
    const value = getCellValue(row, column.dataIndex);
    return (column.render ? column.render(value, row, index) : value) as ReactNode;
  };

  const toggleExpanded = (key: Key) => {
    setExpandedRowKeys((current) => toggleKey(current, key));
  };

  const selectionControl = (key: Key, label: string) => (
    <input
      type="checkbox"
      checked={rowSelection?.selectedRowKeys.includes(key) ?? false}
      onChange={() => handleToggleRow(key)}
      onClick={(event) => event.stopPropagation()}
      aria-label={label}
      className={`${checkboxClass} shrink-0`}
    />
  );

  return (
    <div className={`relative ${className}`}>
      {/* Phones use stacked records so row actions and status never leave the viewport. */}
      {viewport === 'mobile' && (
        <div className="space-y-3">
          {rowSelection && dataSource.length > 0 && (
            <label className="text-foreground-secondary flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={handleToggleAll}
                aria-label="Select all rows"
                className={checkboxClass}
              />
              <span>Select all rows</span>
            </label>
          )}
          {dataSource.length === 0 ? (
            <div className="border-border text-foreground-muted rounded-lg border px-4 py-8 text-center text-sm">
              {emptyText ?? 'No data'}
            </div>
          ) : (
            dataSource.map((row, index) => {
              const key = getRowKey(row, rowKey);
              const rowProps = onRow?.(row, index) ?? {};
              const orderedColumns = [
                ...primaryColumns,
                ...columns.filter((column) => !primaryColumns.includes(column)),
              ];
              return (
                <div
                  key={key}
                  className={`border-border bg-surface dark:bg-surface-inset relative rounded-lg border p-4 shadow-sm ${rowProps.className ?? ''}`}
                  style={rowProps.style}
                >
                  {rowProps.onClick && (
                    <button
                      type="button"
                      className="absolute inset-0 z-0 rounded-lg"
                      onClick={rowProps.onClick}
                      aria-label={`Open row ${String(key)}`}
                    />
                  )}
                  <div className="pointer-events-none relative z-10 space-y-3 [&_a]:pointer-events-auto [&_button]:pointer-events-auto [&_input]:pointer-events-auto">
                    {rowSelection && selectionControl(key, 'Select row')}
                    {orderedColumns.map((column, columnIndex) => (
                      <div
                        key={getColumnKey(column, columnIndex)}
                        className={
                          primaryColumns.includes(column)
                            ? 'text-foreground text-sm font-semibold'
                            : 'grid grid-cols-[minmax(6rem,0.4fr)_minmax(0,1fr)] items-start gap-3 text-sm'
                        }
                      >
                        {!primaryColumns.includes(column) && (
                          <span className="text-foreground-muted">
                            {column.mobileLabel ?? column.title}
                          </span>
                        )}
                        <div className="min-w-0 break-words">{renderCell(column, row, index)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Tablets show priority columns and reveal secondary detail in-place. */}
      {viewport === 'tablet' && (
        <div
          className="border-border w-full overflow-x-hidden overflow-y-auto rounded-lg border"
          style={bodyStyle}
        >
          <table className="w-full table-fixed border-collapse text-sm">
            <thead className="bg-surface-subtle dark:bg-surface-header">
              <tr>
                {rowSelection && (
                  <th className={`${cellPadding} w-12 text-left`}>
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={handleToggleAll}
                      aria-label="Select all rows"
                      className={checkboxClass}
                    />
                  </th>
                )}
                {tabletColumns.map((column, columnIndex) => (
                  <th
                    key={getColumnKey(column, columnIndex)}
                    className={`${cellPadding} text-foreground-secondary font-semibold ${alignClass(column.align)}`}
                  >
                    {column.title}
                  </th>
                ))}
                {detailColumns.length > 0 && <th className={`${cellPadding} w-12`} />}
              </tr>
            </thead>
            <tbody>
              {dataSource.length === 0 ? (
                <tr>
                  <td
                    colSpan={
                      tabletColumns.length + (rowSelection ? 1 : 0) + (detailColumns.length ? 1 : 0)
                    }
                    className="text-foreground-muted px-4 py-8 text-center"
                  >
                    {emptyText ?? 'No data'}
                  </td>
                </tr>
              ) : (
                dataSource.map((row, index) => {
                  const key = getRowKey(row, rowKey);
                  const rowProps = onRow?.(row, index) ?? {};
                  const expanded = expandedRowKeys.has(key);
                  return (
                    <Fragment key={key}>
                      <tr
                        className={`border-border hover:bg-surface-subtle dark:bg-surface-inset border-t transition-colors ${rowProps.className ?? ''}`}
                        style={rowProps.style}
                        onClick={rowProps.onClick}
                      >
                        {rowSelection && (
                          <td className={cellPadding}>{selectionControl(key, 'Select row')}</td>
                        )}
                        {tabletColumns.map((column, columnIndex) => (
                          <td
                            key={getColumnKey(column, columnIndex)}
                            className={`${cellPadding} min-w-0 break-words ${alignClass(column.align)}`}
                          >
                            {renderCell(column, row, index)}
                          </td>
                        ))}
                        {detailColumns.length > 0 && (
                          <td className={cellPadding}>
                            <button
                              type="button"
                              onClick={(event) => {
                                event.stopPropagation();
                                toggleExpanded(key);
                              }}
                              aria-expanded={expanded}
                              aria-label={expanded ? 'Hide row details' : 'Show row details'}
                              className="text-foreground-muted hover:bg-surface-subtle focus-visible:outline-accent rounded p-1 focus-visible:outline-2 focus-visible:outline-offset-2"
                            >
                              <ChevronDown
                                className={`h-4 w-4 transition-transform ${expanded ? 'rotate-180' : ''}`}
                              />
                            </button>
                          </td>
                        )}
                      </tr>
                      {expanded && detailColumns.length > 0 && (
                        <tr className="border-border bg-surface-subtle border-t">
                          <td
                            colSpan={tabletColumns.length + (rowSelection ? 1 : 0) + 1}
                            className="px-4 py-3"
                          >
                            <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
                              {detailColumns.map((column, columnIndex) => (
                                <div key={getColumnKey(column, columnIndex)} className="min-w-0">
                                  <dt className="text-foreground-muted text-xs font-medium">
                                    {column.mobileLabel ?? column.title}
                                  </dt>
                                  <dd className="text-foreground mt-1 text-sm break-words">
                                    {renderCell(column, row, index)}
                                  </dd>
                                </div>
                              ))}
                            </dl>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Wide screens retain the complete data table without imposing a page-wide minimum width. */}
      {viewport === 'desktop' && (
        <div
          className={`border-border w-full overflow-y-auto rounded-lg border ${scroll?.x ? 'overflow-x-auto' : 'overflow-x-hidden'}`}
          style={bodyStyle}
        >
          <table
            className="w-full table-fixed border-collapse text-sm"
            style={scroll?.x ? { minWidth: scroll.x } : undefined}
          >
            <thead className="bg-surface-subtle dark:bg-surface-header">
              <tr>
                {rowSelection && (
                  <th className={`${cellPadding} w-12 text-left`}>
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={handleToggleAll}
                      aria-label="Select all rows"
                      className={checkboxClass}
                    />
                  </th>
                )}
                {columns.map((col, columnIndex) => (
                  <th
                    key={getColumnKey(col, columnIndex)}
                    className={`${cellPadding} text-foreground-secondary font-semibold ${alignClass(col.align)}`}
                    style={{ width: col.width }}
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
                    className="text-foreground-muted px-4 py-8 text-center"
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
                      className={`border-border hover:bg-surface-subtle dark:bg-surface-inset border-t transition-colors ${rowProps.className ?? ''}`}
                      style={rowProps.style}
                      onClick={rowProps.onClick}
                    >
                      {rowSelection && (
                        <td className={cellPadding}>
                          <input
                            type="checkbox"
                            checked={rowSelection.selectedRowKeys.includes(key)}
                            onChange={() => handleToggleRow(key)}
                            onClick={(event) => event.stopPropagation()}
                            aria-label="Select row"
                            className={checkboxClass}
                          />
                        </td>
                      )}
                      {columns.map((col, columnIndex) => {
                        const value = getCellValue(row, col.dataIndex);
                        const content = col.render ? col.render(value, row, index) : value;
                        return (
                          <td
                            key={getColumnKey(col, columnIndex)}
                            className={`${cellPadding} ${alignClass(col.align)} ${col.ellipsis ? 'max-w-[1px] overflow-hidden text-ellipsis whitespace-nowrap' : ''}`}
                            style={{ width: col.width }}
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
      )}

      <AdminTablePagination pagination={pagination} />

      {loading && (
        <div className="bg-surface/70 absolute inset-0 z-10 flex items-center justify-center rounded-lg backdrop-blur-sm">
          <LoadingSpinner size="lg" />
        </div>
      )}
    </div>
  );
}
