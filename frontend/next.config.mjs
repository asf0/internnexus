import dotenv from 'dotenv';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import withBundleAnalyzer from '@next/bundle-analyzer';

const frontendRoot = dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: resolve(frontendRoot, '../.env') });

/** @type {import('next').NextConfig} */
const configuredBackendUrl = process.env.BACKEND_URL;
const backendDestination =
  typeof configuredBackendUrl === 'string' && configuredBackendUrl.length > 0
    ? configuredBackendUrl.concat('/:path*')
    : 'http://localhost:8000/:path*';
const allowedDevOrigins = (process.env.ALLOWED_DEV_ORIGINS || '')
  .split(',')
  .map((origin) => origin.trim())
  .filter(Boolean);

const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  // Cloudflare's edge compresses responses. Next's own gzip streams produced
  // the repeated `MaxListenersExceededWarning: 11 drain listeners added to
  // [Gzip]` on large responses (companies directory, sitemap chunks). Letting
  // the edge compress removes that CPU/memory churn; direct localhost access
  // simply serves uncompressed responses.
  compress: false,
  ...(allowedDevOrigins.length > 0 ? { allowedDevOrigins } : {}),
  turbopack: {
    root: frontendRoot,
  },

  async rewrites() {
    return [
      // Next.js matches rewrites in order and stops at the first hit. This
      // identity rewrite makes /api/auth/* match here first so NextAuth's
      // own route handler (app/api/auth/[...nextauth]/route.ts) keeps
      // serving it, instead of falling through to the generic /api/:path*
      // rule below and getting proxied to the backend (which has no
      // matching routes and 404s).
      {
        source: '/api/auth/:path*',
        destination: '/api/auth/:path*',
      },
      {
        source: '/api/:path*',
        destination: backendDestination,
      },
    ];
  },
};

export default process.env.ANALYZE === 'true'
  ? withBundleAnalyzer({ enabled: true, openAnalyzer: false })(nextConfig)
  : nextConfig;
