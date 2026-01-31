import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 将 /api/* 请求代理到后端
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8080';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
