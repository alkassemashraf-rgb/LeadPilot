import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  // Skip type-checking and linting during Docker/CI builds
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  async redirects() {
    return [
      {
        source: '/admin',
        destination: '/login',
        permanent: true,
      },
      {
        source: '/sign-in',
        destination: '/login',
        permanent: true,
      },
      {
        source: '/sign-up',
        destination: '/signup',
        permanent: true,
      }
    ];
  },
};

export default nextConfig;
