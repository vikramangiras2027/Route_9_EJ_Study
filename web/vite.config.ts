import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Project-site URL: https://vikramangiras2027.github.io/Route_9_EJ_Study/
// Must match the GitHub repository name exactly (case-sensitive).
const repoBase = "/Route_9_EJ_Study/";

export default defineConfig({
  base: process.env.GITHUB_PAGES === "1" ? repoBase : "./",
  plugins: [react(), tailwindcss()],
  build: { target: "es2022", chunkSizeWarningLimit: 700 },
});

