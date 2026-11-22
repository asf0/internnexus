import { describe, expect, it, vi } from 'vitest';

vi.mock('@/auth', () => ({ auth: (handler: unknown) => handler }));

import { buildCsp } from '@/proxy';

describe('proxy CSP', () => {
  it('binds scripts to the per-request nonce', () => {
    const csp = buildCsp('nonce-value');
    expect(csp).toContain("script-src 'self' 'nonce-nonce-value'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).not.toContain("script-src 'self' 'unsafe-inline'");
  });
});
