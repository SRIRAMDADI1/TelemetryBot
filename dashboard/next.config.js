/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    // Unused for in-project tab switches (those are client-side). Kept for
    // project-to-project navigations and Refresh.
    staleTimes: { dynamic: 30, static: 180 },
  },
};

module.exports = nextConfig;
