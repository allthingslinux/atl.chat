// @ts-check

import { setupDevPlatform } from "@cloudflare/next-on-pages/next-dev";

/** @type {import('next').NextConfig} */
const nextConfig = {
	reactStrictMode: true,
	poweredByHeader: false,
	pageExtensions: ["js", "jsx", "ts", "tsx", "md", "mdx"],
};

if (process.env.NODE_ENV === "development") {
	await setupDevPlatform();
}

export default nextConfig;
