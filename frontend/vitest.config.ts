import path from 'node:path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
      'next-auth/react': path.resolve(__dirname, 'tests/stubs/next-auth-react.tsx'),
      'server-only': path.resolve(__dirname, 'tests/stubs/server-only.ts'),
    },
  },
  test: {
    environment: 'happy-dom',
    include: ['tests/unit/**/*.test.{ts,tsx}'],
    setupFiles: ['./tests/setup.ts'],
    // Vitest 5 defaults clearMocks to true; some tests assert on mock calls
    // recorded at module-import time (e.g. tests/unit/auth.config.test.ts),
    // so keep the pre-v5 behavior of not clearing between tests.
    clearMocks: false,
  },
});
