import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import McpUsageClient from '@/app/admin/agent-usage/McpUsageClient';

const stats = {
  total_calls: 120,
  calls_today: 12,
  calls_this_week: 48,
  calls_this_month: 100,
  success_rate: 97.5,
  average_duration_ms: 18.4,
  unique_users: 8,
  unique_keys: 10,
  search_count: 42,
  average_search_result_count: 13.2,
};

const filters = { tool: '', status: '', dateFrom: '', dateTo: '', page: 1 };

afterEach(cleanup);

describe('McpUsageClient', () => {
  it('renders summaries, breakdowns, filters, and recent events', () => {
    render(
      <McpUsageClient
        stats={stats}
        tools={[
          {
            tool_name: 'search_jobs',
            total_calls: 42,
            successful_calls: 40,
            failed_calls: 2,
            success_rate: 95.2,
            average_duration_ms: 21,
            average_result_count: 13.2,
          },
        ]}
        daily={[
          {
            date: '2026-07-14',
            total_calls: 12,
            successful_calls: 11,
            failed_calls: 1,
            unique_users: 4,
          },
        ]}
        events={{
          items: [
            {
              id: 'event-1',
              user_id: 'user-1',
              mcp_key_id: 'key-1',
              tool_name: 'search_jobs',
              called_at: '2026-07-14T12:00:00Z',
              success: true,
              duration_ms: 20,
              job_id: null,
              result_count: 8,
              error_category: null,
              metadata: { query: 'python' },
            },
          ],
          total: 1,
          page: 1,
          page_size: 50,
          total_pages: 1,
        }}
        filters={filters}
      />
    );

    expect(screen.getByRole('heading', { name: 'MCP usage' })).toBeInTheDocument();
    expect(screen.getByText('97.5%')).toBeInTheDocument();
    expect(screen.getAllByText('search_jobs').length).toBeGreaterThan(0);
    expect(screen.getByLabelText('Status')).toBeInTheDocument();
    expect(screen.getByText('SUCCESS')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Reset' })).toHaveAttribute(
      'href',
      '/admin/agent-usage'
    );
  });

  it('renders independent failure states for partial analytics failures', () => {
    render(
      <McpUsageClient stats={stats} tools={null} daily={null} events={null} filters={filters} />
    );
    expect(screen.getByText('Failed to load tool breakdown.')).toBeInTheDocument();
    expect(screen.getByText('Failed to load daily activity.')).toBeInTheDocument();
    expect(screen.getByText('Failed to load recent MCP events.')).toBeInTheDocument();
  });
});
