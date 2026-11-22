'use client';

import { useMemo, useState } from 'react';
import { Check, Copy, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui';

type ClientName = 'generic' | 'codex' | 'opencode';

interface McpSetupGuideProps {
  readonly endpoint: string;
}

function CopyBlock({ label, value }: { readonly label: string; readonly value: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="border-border overflow-hidden rounded-lg border">
      <div className="bg-surface-subtle flex items-center justify-between px-3 py-2">
        <span className="text-foreground-muted text-xs font-medium">{label}</span>
        <Button variant="ghost" onClick={copy} aria-label={`Copy ${label}`}>
          {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          {copied ? 'Copied' : 'Copy'}
        </Button>
      </div>
      {/* eslint-disable jsx-a11y/no-noninteractive-tabindex -- Keyboard users must be able to scroll long code samples. */}
      <section
        className="focus:ring-focus-ring overflow-x-auto bg-slate-950 p-4 text-xs leading-5 text-slate-100 focus:ring-2 focus:outline-none"
        aria-label={`${label} code block`}
        tabIndex={0}
      >
        <pre>
          <code>{value}</code>
        </pre>
      </section>
      {/* eslint-enable jsx-a11y/no-noninteractive-tabindex */}
    </div>
  );
}

export function McpSetupGuide({ endpoint }: McpSetupGuideProps) {
  const [client, setClient] = useState<ClientName>('generic');
  const snippets = useMemo(
    () => ({
      generic: `Endpoint: ${endpoint}\nAuthorization: Bearer \${INTERNNEXUS_MCP_API_KEY}`,
      codex: `[mcp_servers.internnexus]\nurl = "${endpoint}"\nbearer_token_env_var = "INTERNNEXUS_MCP_API_KEY"`,
      opencode: `{
  "mcp": {
    "internnexus": {
      "type": "remote",
      "url": "${endpoint}",
      "oauth": false,
      "headers": {
        "Authorization": "Bearer {env:INTERNNEXUS_MCP_API_KEY}"
      }
    }
  }
}`,
    }),
    [endpoint]
  );

  const labels: Record<ClientName, string> = {
    generic: 'Generic',
    codex: 'Codex',
    opencode: 'OpenCode',
  };

  return (
    <div className="space-y-6">
      <section aria-labelledby="mcp-step-2">
        <h3 id="mcp-step-2" className="font-semibold">
          2. Store the key securely
        </h3>
        <p className="text-foreground-muted mt-1 text-sm">
          Save the one-time value in an environment variable. Never paste the key into a config file
          or commit it to source control.
        </p>
        <div className="mt-3">
          <CopyBlock
            label="Environment variable"
            value="INTERNNEXUS_MCP_API_KEY=<paste the one-time key here>"
          />
        </div>
      </section>

      <section aria-labelledby="mcp-step-3">
        <h3 id="mcp-step-3" className="font-semibold">
          3. Configure your client
        </h3>
        <p className="text-foreground-muted mt-1 text-sm">
          Connect to the Streamable HTTP endpoint below. These snippets only reference your
          environment variable; they never contain the secret itself.
        </p>
        <div className="border-border mt-3 flex border-b" role="tablist" aria-label="MCP client">
          {(Object.keys(labels) as ClientName[]).map((name) => (
            <button
              key={name}
              type="button"
              role="tab"
              aria-selected={client === name}
              onClick={() => setClient(name)}
              className={`border-b-2 px-4 py-2 text-sm font-medium ${
                client === name
                  ? 'border-accent text-accent'
                  : 'text-foreground-muted hover:text-foreground border-transparent'
              }`}
            >
              {labels[name]}
            </button>
          ))}
        </div>
        <div className="mt-3" role="tabpanel">
          <CopyBlock label={`${labels[client]} configuration`} value={snippets[client]} />
        </div>
        {client === 'opencode' && (
          <a
            href="https://opencode.ai/docs/mcp-servers"
            target="_blank"
            rel="noreferrer"
            className="text-accent mt-2 inline-flex items-center gap-1 text-sm hover:underline"
          >
            OpenCode MCP configuration <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </section>

      <section aria-labelledby="mcp-step-4">
        <h3 id="mcp-step-4" className="font-semibold">
          4. Test the connection
        </h3>
        <p className="text-foreground-muted mt-1 text-sm">
          Try these prompts after refreshing your client&apos;s MCP tool list:
        </p>
        <ul className="text-foreground-secondary mt-3 list-disc space-y-1 pl-5 text-sm">
          <li>Find software internships in Denver and show the total number of matches.</li>
          <li>Fetch the next page if the search has more results.</li>
          <li>Save the best two jobs, then list my saved jobs.</li>
          <li>Get the application link for the best match without marking it applied.</li>
        </ul>
      </section>

      <div className="bg-accent/15 text-foreground rounded-lg p-4 text-sm">
        <p className="font-semibold">Search and permission notes</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>
            Searches default to active jobs posted in the last 120 days and return up to 50 per
            page.
          </li>
          <li>
            Use dedicated location, company, category, job type, and work mode filters. Separate
            multiple filter values with a pipe (<code>|</code>).
          </li>
          <li>
            <code>match_mode=&quot;all&quot;</code> requires every keyword; use <code>any</code>,
            fewer filters, or <code>posted_within=&quot;all&quot;</code> to broaden sparse searches.
          </li>
          <li>
            Inspect <code>total</code> and <code>next_page</code>, then request another page when
            needed.
          </li>
          <li>
            Use <code>get_job</code> for full details only after selecting candidates.
          </li>
          <li>
            <code>get_application_link</code> requests a tracked employer link without changing your
            applied state. <code>apply_to_job</code> requests the link and marks the job applied.
          </li>
          <li>
            Agents can search, read, save, unsave, mark applied, and unmark applied jobs. They
            cannot access your profile, password, resume, or admin tools.
          </li>
        </ul>
        <p className="mt-2">
          Revoke a key below at any time. Connected clients using it will immediately lose access.
        </p>
      </div>
    </div>
  );
}
