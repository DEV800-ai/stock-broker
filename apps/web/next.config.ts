import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      { source: "/watchlist", destination: "/ideas", permanent: false },
      { source: "/scanner", destination: "/ideas", permanent: false },
    ];
  },
};

export default nextConfig;
