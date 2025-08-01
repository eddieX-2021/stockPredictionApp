import type { NextConfig } from "next";

const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'localhost:3000',
        port: '',
        pathname: '/'
      }
    ]
  }
};
export default nextConfig;
