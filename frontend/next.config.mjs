import dotenv from 'dotenv';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const frontendRoot = dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: resolve(frontendRoot, '../.env') });

/** @type {import('next').NextConfig} */
const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  allowedDevOrigins: ['192.168.0.174:3000', 'localhost:3000'],
  turbopack: {
    root: frontendRoot,
  },

  async rewrites() {
    return [
      {
        source: '/api/auth/:path*',
        destination: '/api/auth/:path*',
      },
      {
        source: '/api/:path*',
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};
export default nextConfig;
