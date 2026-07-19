import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "./",
  plugins: [react()],
  build: {
    outDir: "../dashboard",
    emptyOutDir: true,
    sourcemap: false,
  },
});
