/** @type {import('next').NextConfig} */
const isPages = process.env.DEPLOY_TARGET === "gh-pages";
const basePath = isPages ? (process.env.NEXT_PUBLIC_BASE_PATH || "") : "";

const nextConfig = {
  output: isPages ? "export" : "standalone",
  trailingSlash: isPages,
  basePath: isPages ? basePath : undefined,
  assetPrefix: isPages ? basePath : undefined,
  images: isPages ? { unoptimized: true } : undefined,
};

module.exports = nextConfig;

