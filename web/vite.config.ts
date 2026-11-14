import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// `base: "./"` keeps every asset URL relative, so the static build can be
// hosted anywhere: GitHub Pages project sites, a university web folder, S3, etc.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  build: { target: "es2022", chunkSizeWarningLimit: 700 },
});
