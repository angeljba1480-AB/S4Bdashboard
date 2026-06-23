/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Allow importing TS source from the shared workspace package.
  transpilePackages: ["@private-ai/shared"],
};

export default nextConfig;
