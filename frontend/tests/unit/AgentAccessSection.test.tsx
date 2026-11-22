import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AgentAccessSection } from '@/components/settings/AgentAccessSection';
import type { MCPApiKey } from '@/lib/types/user';

const mocks = vi.hoisted(() => ({
  createMCPApiKey: vi.fn(),
  revokeMCPApiKey: vi.fn(),
}));

vi.mock('@/app/actions/user', () => ({
  createMCPApiKey: mocks.createMCPApiKey,
  revokeMCPApiKey: mocks.revokeMCPApiKey,
}));

const activeKey: MCPApiKey = {
  id: 'key-1',
  name: 'Codex',
  key_prefix: 'inx_mcp_preview',
  created_at: '2026-07-01T00:00:00Z',
  expires_at: '2026-10-01T00:00:00Z',
  last_used_at: null,
  revoked_at: null,
};

describe('AgentAccessSection', () => {
  beforeEach(() => {
    mocks.createMCPApiKey.mockReset();
    mocks.revokeMCPApiKey.mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('creates a key and displays the one-time secret', async () => {
    const user = userEvent.setup();
    mocks.createMCPApiKey.mockResolvedValue({
      success: true,
      data: { ...activeKey, secret: 'inx_mcp_one_time_secret' },
    });
    render(<AgentAccessSection initialKeys={[]} mcpEndpoint="https://mcp.example.com/mcp" />);

    await user.clear(screen.getByLabelText('Key name'));
    await user.type(screen.getByLabelText('Key name'), 'Codex');
    await user.selectOptions(screen.getByLabelText('Key expiration'), '30');
    await user.click(screen.getByRole('button', { name: /create key/i }));

    await waitFor(() => expect(mocks.createMCPApiKey).toHaveBeenCalledWith('Codex', 30));
    expect(screen.getByText('inx_mcp_one_time_secret')).toBeInTheDocument();
    expect(screen.getByText(/copy this key now/i)).toBeInTheDocument();
    expect(screen.getAllByText('Codex').length).toBeGreaterThan(0);
  });

  it('revokes an owned key after confirmation', async () => {
    const user = userEvent.setup();
    const confirm = vi.fn(() => true);
    vi.stubGlobal('confirm', confirm);
    Object.defineProperty(window, 'confirm', { configurable: true, value: confirm });
    mocks.revokeMCPApiKey.mockResolvedValue({ success: true });
    render(
      <AgentAccessSection initialKeys={[activeKey]} mcpEndpoint="https://mcp.example.com/mcp" />
    );

    await user.click(screen.getByRole('button', { name: 'Revoke Codex' }));

    await waitFor(() => expect(mocks.revokeMCPApiKey).toHaveBeenCalledWith('key-1'));
    expect(screen.queryByText('inx_mcp_preview…')).not.toBeInTheDocument();
  });
});
