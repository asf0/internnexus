'use client';

import { useState } from 'react';
import { Bot, Copy, KeyRound, Loader2, Trash2 } from 'lucide-react';
import { createMCPApiKey, revokeMCPApiKey } from '@/app/actions/user';
import { Alert, Button, Card, CardContent, Input, Select } from '@/components/ui';
import type { MCPApiKey } from '@/lib/types/user';
import { McpSetupGuide } from './McpSetupGuide';

interface AgentAccessSectionProps {
  readonly initialKeys: MCPApiKey[];
  readonly mcpEndpoint: string;
}

export function AgentAccessSection({ initialKeys, mcpEndpoint }: AgentAccessSectionProps) {
  const [keys, setKeys] = useState(initialKeys);
  const [name, setName] = useState('My AI agent');
  const [days, setDays] = useState(90);
  const [secret, setSecret] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const createKey = async () => {
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    setSecret(null);
    const result = await createMCPApiKey(name.trim(), days);
    if (result.success && result.data) {
      setKeys((current) => [result.data!, ...current]);
      setSecret(result.data.secret);
    } else setError(result.error || 'Failed to create key');
    setBusy(false);
  };

  const revokeKey = async (id: string) => {
    if (!window.confirm('Revoke this MCP key? Connected agents will immediately lose access.'))
      return;
    const result = await revokeMCPApiKey(id);
    if (result.success) setKeys((current) => current.filter((key) => key.id !== id));
    else setError(result.error || 'Failed to revoke key');
  };

  return (
    <Card>
      <CardContent>
        <div className="mb-5 flex items-start gap-3">
          <Bot className="text-accent mt-0.5 h-5 w-5" />
          <div>
            <h2 className="text-foreground text-xl font-semibold">AI agent access</h2>
            <p className="text-foreground-muted mt-1 text-sm">
              Connect Codex, OpenCode, or another MCP client to search and organize InternNexus
              jobs.
            </p>
          </div>
        </div>

        <section aria-labelledby="mcp-step-1" className="mb-6">
          <h3 id="mcp-step-1" className="font-semibold">
            1. Create and copy a key
          </h3>
          <p className="text-foreground-muted mt-1 text-sm">
            Keys are scoped to your account. The complete secret is displayed only once.
          </p>
          {error && (
            <Alert type="error" className="mt-4">
              {error}
            </Alert>
          )}
          {secret && (
            <Alert type="success" className="mt-4">
              <p className="font-medium">Copy this key now. It will not be shown again.</p>
              <div className="mt-2 flex items-center gap-2">
                <code className="min-w-0 flex-1 text-xs break-all">{secret}</code>
                <Button variant="secondary" onClick={() => navigator.clipboard.writeText(secret)}>
                  <Copy className="h-4 w-4" /> Copy
                </Button>
              </div>
            </Alert>
          )}
          <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_150px_auto]">
            <Input
              value={name}
              maxLength={100}
              onChange={(event) => setName(event.target.value)}
              aria-label="Key name"
            />
            <Select
              value={days}
              onChange={(event) => setDays(Number(event.target.value))}
              aria-label="Key expiration"
            >
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
              <option value={180}>180 days</option>
              <option value={365}>365 days</option>
            </Select>
            <Button onClick={createKey} disabled={busy || !name.trim()}>
              {busy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <KeyRound className="h-4 w-4" />
              )}{' '}
              Create key
            </Button>
          </div>
        </section>

        <McpSetupGuide endpoint={mcpEndpoint} />

        <section className="mt-6" aria-labelledby="mcp-active-keys">
          <h3 id="mcp-active-keys" className="mb-3 font-semibold">
            Your MCP keys
          </h3>
          <div className="space-y-3">
            {keys.length === 0 && <p className="text-foreground-muted text-sm">No MCP keys yet.</p>}
            {keys.map((key) => (
              <div
                key={key.id}
                className="border-border flex items-center justify-between gap-3 rounded-lg border p-3"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{key.name}</p>
                  <p className="text-foreground-muted text-xs">
                    <code>{key.key_prefix}…</code> · expires{' '}
                    {new Date(key.expires_at).toLocaleDateString()}
                    {key.last_used_at
                      ? ` · last used ${new Date(key.last_used_at).toLocaleDateString()}`
                      : ''}
                  </p>
                </div>
                {key.revoked_at ? (
                  <span className="text-foreground-muted text-xs">Revoked</span>
                ) : (
                  <Button
                    variant="ghost"
                    onClick={() => revokeKey(key.id)}
                    aria-label={`Revoke ${key.name}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </section>
      </CardContent>
    </Card>
  );
}
