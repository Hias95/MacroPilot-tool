import type { NextConfig } from "next";

/**
 * Zwei Betriebsarten:
 *  - lokal: Next-Dev-Server plus FastAPI (NEXT_PUBLIC_API_URL).
 *  - statisch (D2): NEXT_PUBLIC_DATA_MODE=static exportiert eine reine HTML/JS-Seite, die JSON-Dateien aus
 *    public/data liest (taeglicher Export in GitHub Actions). NEXT_PUBLIC_BASE_PATH fuer GitHub Pages unter /<repo>.
 */
const isStatic = process.env.NEXT_PUBLIC_DATA_MODE === "static";
const basePath = (process.env.NEXT_PUBLIC_BASE_PATH ?? "").replace(/\/$/, "");

const nextConfig: NextConfig = {
  // Eigenes Build-Verzeichnis, damit ein statischer Build neben dem laufenden Dev-Server nicht kollidiert.
  ...(isStatic ? { output: "export", distDir: ".next-static", trailingSlash: true, images: { unoptimized: true } } : {}),
  ...(basePath ? { basePath, assetPrefix: basePath } : {}),
};

export default nextConfig;
