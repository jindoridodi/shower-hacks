import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack(config) {
    // Allow imports from the monorepo root (e.g. data/fixtures/)
    config.resolve.modules = [
      ...(config.resolve.modules || []),
      path.resolve(__dirname, "../.."),
    ];
    return config;
  },
};

export default nextConfig;
