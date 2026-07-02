import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // App autocontenida dentro del monorepo: fija la raíz de tracing a esta carpeta
  // para que Vercel no infiera la raíz del workspace por múltiples lockfiles.
  outputFileTracingRoot: __dirname,
};

export default nextConfig;
