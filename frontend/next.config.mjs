/** @type {import('next').NextConfig} */
const api = process.env.API_INTERNAL_URL || "http://127.0.0.1:8010";
const basePath = (process.env.NEXT_BASE_PATH || "").replace(/\/$/, "");
const nextConfig = {
  output: "standalone",
  ...(basePath ? { basePath } : {}),
  async rewrites() {
    return [{ source: "/backend/:path*", destination: `${api}/:path*` }];
  },
};
export default nextConfig;
