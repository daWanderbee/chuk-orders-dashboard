/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // A stray package-lock.json in the home dir makes Next infer the wrong
  // workspace root; pin it to this project.
  outputFileTracingRoot: import.meta.dirname,
};

export default nextConfig;
