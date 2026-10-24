import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: "localhost",
      strictPort: true,
      proxy: {
        "/api": {
          target: env.API_PROXY_TARGET || "http://localhost:8000",
          changeOrigin: false,
          rewrite: (path: string) => path.replace(/^\/api/, "") || "/",
        },
      },
    },
  };
});
