import { describe, expect, it } from 'vitest';
import { isSafeInternalPath } from '@/lib/navigation';

describe('isSafeInternalPath', () => {
  it.each(['/jobs/123', '/admin?tab=jobs', '/profile#notifications'])(
    'accepts internal path %s',
    (path) => expect(isSafeInternalPath(path)).toBe(true)
  );

  it.each(['https://evil.example', '//evil.example', '/\\evil.example', 'javascript:alert(1)'])(
    'rejects unsafe callback %s',
    (path) => expect(isSafeInternalPath(path)).toBe(false)
  );
});
