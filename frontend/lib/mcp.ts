const DEFAULT_MCP_ORIGIN = 'http://localhost:8001';

function withoutTrailingSlashes(value: string): string {
  let end = value.length;
  while (end > 0 && value[end - 1] === '/') end -= 1;
  return value.slice(0, end);
}

/** Normalize a configured MCP origin or URL to its Streamable HTTP endpoint. */
export function getMcpEndpoint(configuredUrl?: string): string {
  const value = configuredUrl?.trim() || DEFAULT_MCP_ORIGIN;
  try {
    const url = new URL(value);
    url.pathname = '/mcp';
    url.search = '';
    url.hash = '';
    return url.toString().replace(/\/$/, '');
  } catch {
    return `${withoutTrailingSlashes(value)}/mcp`;
  }
}
