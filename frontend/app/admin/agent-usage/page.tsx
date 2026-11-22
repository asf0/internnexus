import { getBackendToken } from '@/lib/auth.server';
import { fetchAdminData } from '@/lib/admin-api';
import McpUsageClient from './McpUsageClient';
import type { McpDailyUsage, McpToolUsage, McpUsageEventsResponse, McpUsageStats } from './types';

interface SearchParams {
  readonly tool?: string;
  readonly status?: string;
  readonly date_from?: string;
  readonly date_to?: string;
  readonly page?: string;
}

export default async function McpUsagePage({
  searchParams,
}: {
  readonly searchParams: Promise<SearchParams>;
}) {
  const tokenResult = await getBackendToken();
  if (!tokenResult.ok) {
    return (
      <div role="alert" className="rounded border border-red-800 p-4 text-sm text-red-300">
        Admin token unavailable. Please sign in again.
      </div>
    );
  }

  const params = await searchParams;
  const page = Math.max(1, Number.parseInt(params.page || '1', 10) || 1);
  const eventQuery = new URLSearchParams({ page: String(page), page_size: '50' });
  if (params.tool) eventQuery.set('tool', params.tool);
  if (params.status) eventQuery.set('status', params.status);
  if (params.date_from) eventQuery.set('date_from', params.date_from);
  if (params.date_to) eventQuery.set('date_to', params.date_to);

  const [stats, tools, daily, events] = await Promise.all([
    fetchAdminData<McpUsageStats>('/admin/mcp-usage/stats'),
    fetchAdminData<McpToolUsage[]>('/admin/mcp-usage/tools'),
    fetchAdminData<McpDailyUsage[]>('/admin/mcp-usage/daily?days=30'),
    fetchAdminData<McpUsageEventsResponse>(`/admin/mcp-usage/events?${eventQuery.toString()}`),
  ]);

  if (!stats) {
    return (
      <div role="alert" className="rounded border border-red-800 p-4 text-sm text-red-300">
        Failed to load MCP usage analytics. Please try again.
      </div>
    );
  }

  return (
    <McpUsageClient
      stats={stats}
      tools={tools}
      daily={daily}
      events={events}
      filters={{
        tool: params.tool || '',
        status: params.status || '',
        dateFrom: params.date_from || '',
        dateTo: params.date_to || '',
        page,
      }}
    />
  );
}
