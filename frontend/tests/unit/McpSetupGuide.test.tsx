import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { McpSetupGuide } from '@/components/settings/McpSetupGuide';

afterEach(cleanup);

describe('McpSetupGuide', () => {
  it('renders Generic, Codex, and OpenCode snippets with the configured endpoint', async () => {
    const user = userEvent.setup();
    render(<McpSetupGuide endpoint="https://mcp.example.com/mcp" />);

    expect(screen.getByText(/Endpoint: https:\/\/mcp.example.com\/mcp/)).toBeInTheDocument();
    await user.click(screen.getByRole('tab', { name: 'Codex' }));
    expect(screen.getByText(/\[mcp_servers\.internnexus\]/)).toBeInTheDocument();
    expect(screen.getByText(/bearer_token_env_var/)).toBeInTheDocument();
    await user.click(screen.getByRole('tab', { name: 'OpenCode' }));
    expect(screen.getByText(/\{env:INTERNNEXUS_MCP_API_KEY\}/)).toBeInTheDocument();
    expect(screen.getByText(/"oauth": false/)).toBeInTheDocument();
  });

  it('copies configuration by environment-variable reference and never a one-time secret', async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
    render(<McpSetupGuide endpoint="https://mcp.example.com/mcp" />);

    await user.click(screen.getByRole('button', { name: 'Copy Generic configuration' }));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining('INTERNNEXUS_MCP_API_KEY'));
    expect(writeText.mock.calls[0][0]).not.toContain('inx_mcp_');
  });
});
