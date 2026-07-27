/**
 * Purpose: Next.js framework configuration for the frontend app.
 * Interactions: Read by `next dev` and `next build`. Affects how the app in
 * src/app/ is compiled and served; currently uses default settings.
 */
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for the slim production image in apps/frontend/Dockerfile
  output: "standalone",
};

export default nextConfig;
