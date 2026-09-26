/** @type {import('next').NextConfig} */
const api = process.env.API_INTERNAL_URL || "http://127.0.0.1:8010";
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/backend/:path*", destination: `${api}/:path*` }];
  },
};
export default nextConfig;
