import { describe, expect, it } from 'vitest';
import { getMcpEndpoint } from '@/lib/mcp';

describe('getMcpEndpoint', () => {
  it('normalizes an origin and existing path to /mcp', () => {
    expect(getMcpEndpoint('https://agents.example.com/')).toBe('https://agents.example.com/mcp');
    expect(getMcpEndpoint('https://agents.example.com/old/path?token=nope')).toBe(
      'https://agents.example.com/mcp'
    );
  });

  it('uses the local MCP service by default', () => {
    expect(getMcpEndpoint()).toBe('http://localhost:8001/mcp');
  });
});
