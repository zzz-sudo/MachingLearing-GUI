import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteStaticCopy } from "vite-plugin-static-copy";

export default defineConfig({
  plugins: [
    react(),
    viteStaticCopy({
      targets: ["cmaps", "standard_fonts", "wasm", "iccs"].map((directory) => ({
        src: `node_modules/pdfjs-dist/${directory}/*`,
        dest: `pdfjs/${directory}`,
      })),
    }),
  ],
  server: {
    port: 5173,
    strictPort: true,
  },
});
