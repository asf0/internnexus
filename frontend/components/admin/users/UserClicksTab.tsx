import { AdminCard, AdminTable } from '@/components/admin/ui';
import type { AdminColumn } from '@/components/admin/ui';
import { type PaginatedResponse, type UserClick } from '@/app/actions/admin';
import { formatDate } from './types';

interface UserClicksTabProps {
  readonly clicksData: PaginatedResponse<UserClick> | null;
  readonly clicksLoading: boolean;
  readonly clicksPage: number;
  readonly pageSize: number;
  readonly onPageChange: (page: number) => void;
}

const clickColumns: AdminColumn<UserClick>[] = [
  { title: 'Job Title', dataIndex: 'job_title', key: 'job_title', ellipsis: true },
  { title: 'Company', dataIndex: 'company', key: 'company', ellipsis: true },
  {
    title: 'Clicked At',
    dataIndex: 'clicked_at',
    key: 'clicked_at',
    width: 180,
    render: (date: string) => formatDate(date),
  },
];

export function UserClicksTab({
  clicksData,
  clicksLoading,
  clicksPage,
  pageSize,
  onPageChange,
}: UserClicksTabProps) {
  return (
    <AdminCard className="shadow-sm">
      <AdminTable
        columns={clickColumns}
        dataSource={clicksData?.items || []}
        rowKey="id"
        loading={clicksLoading}
        pagination={
          clicksData
            ? {
                current: clicksPage,
                pageSize,
                total: clicksData.total,
                onChange: onPageChange,
              }
            : false
        }
        emptyText="No click history found for this user"
      />
    </AdminCard>
  );
}
