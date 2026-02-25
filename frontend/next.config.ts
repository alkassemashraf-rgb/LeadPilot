import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  // Skip type-checking and linting during Docker/CI builds — these run
  // separately in pre-commit hooks and GitHub Actions where errors are surfaced.
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
