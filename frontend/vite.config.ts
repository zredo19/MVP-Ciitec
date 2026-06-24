import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// PWA (RF-010): app shell precacheada + caché de GET de briefings para
// lectura offline. La cola de cargas offline se maneja en src/offline.ts.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "Síntesis de Briefings — CIITEC",
        short_name: "Briefings",
        lang: "es",
        theme_color: "#2c3e50",
        background_color: "#ffffff",
        display: "standalone",
        start_url: "/",
        icons: [],
      },
      workbox: {
        navigateFallbackDenylist: [/^\/api/, /^\/ws/],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith("/api/briefings"),
            handler: "NetworkFirst",
            options: {
              cacheName: "briefings-cache",
              expiration: { maxEntries: 50, maxAgeSeconds: 86400 },
            },
          },
        ],
      },
    }),
  ],
  server: {
    host: "0.0.0.0",
    port: 5173,
    // Detrás de Nginx el origen es el mismo; en dev directo se puede proxyear.
    proxy: {
      "/api": { target: "http://api:8000", changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, "") },
    },
  },
});
