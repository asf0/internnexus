import dotenv from 'dotenv';
import { resolve } from 'path';
dotenv.config({ path: resolve('../.env') });

/** @type {import('next').NextConfig} */
const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  allowedDevOrigins: ['192.168.0.174:3000', 'localhost:3000'],

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
