/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [
      {
        source: '/login',
        destination: '/',
        permanent: true,
      },
      {
        source: '/register',
        destination: '/',
        permanent: true,
      },
      {
        source: '/set-password',
        destination: '/settings',
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
