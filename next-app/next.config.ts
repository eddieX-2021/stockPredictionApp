import type { NextConfig } from "next";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const appDir = dirname(fileURLToPath(import.meta.url));

const nextConfig = {
  turbopack: {
    root: appDir,
  },
} satisfies NextConfig;

export default nextConfig;