import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Сборка кладётся в frontend/dist и отдаётся Python-бэкендом.
// В dev (`npm run dev`) проксируем /api на бэкенд :8000.
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
