import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    define: {
      "import.meta.env.VITE_PUBLIC_DEMO": JSON.stringify(
        mode === "demo" ? "true" : "false",
      ),
    },
    plugins: [
      react(),
      tailwindcss(),
      ...(mode === "demo"
        ? [
            {
              name: "isolated-demo",
              transformIndexHtml(html: string) {
                return html
                  .replace(
                    "<head>",
                    `<head><meta http-equiv="Content-Security-Policy" content="default-src 'self'; connect-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'">`,
                  )
                  .replace(
                    "<title>inbox-nizer</title>",
                    "<title>Inbox-nizer — Interactive Demo</title>",
                  );
              },
              generateBundle() {
                this.emitFile({
                  type: "asset",
                  fileName: "demo-build.json",
                  source: JSON.stringify({
                    mode: "synthetic-demo",
                    commit: process.env.RENDER_GIT_COMMIT || "local",
                  }),
                });
              },
            } satisfies Plugin,
          ]
        : []),
    ],
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
