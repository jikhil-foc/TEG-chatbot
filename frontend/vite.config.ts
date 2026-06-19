import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import {
  rewriteLocationHeader,
  rewriteTegContent,
  shouldRewriteContent,
  stripFrameBlockingHeaders,
} from "./vite-teg-proxy";

export default defineConfig(({ mode }) => {
  if (mode === "widget") {
    return {
      plugins: [react()],
      resolve: {
        alias: { "@": resolve(__dirname, "src") },
      },
      build: {
        outDir: "dist/widget",
        emptyOutDir: true,
        lib: {
          entry: resolve(__dirname, "src/embed.tsx"),
          name: "TegChatbot",
          formats: ["iife"],
          fileName: () => "teg-chatbot.js",
        },
        rollupOptions: {
          output: {
            assetFileNames: "teg-chatbot.[ext]",
            inlineDynamicImports: true,
          },
        },
        cssCodeSplit: false,
      },
    };
  }

  return {
    plugins: [react()],
    resolve: {
      alias: { "@": resolve(__dirname, "src") },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
          changeOrigin: true,
        },
        "/teg-site": {
          target: "https://www.teg.ie",
          changeOrigin: true,
          selfHandleResponse: true,
          rewrite: (path) => path.replace(/^\/teg-site/, ""),
          configure: (proxy) => {
            proxy.on("proxyReq", (proxyReq) => {
              proxyReq.setHeader("accept-encoding", "identity");
            });

            proxy.on("proxyRes", (proxyRes, _req, res) => {
              stripFrameBlockingHeaders(proxyRes.headers);

              const location = proxyRes.headers.location;
              if (typeof location === "string") {
                proxyRes.headers.location = rewriteLocationHeader(location);
              }

              const contentType = String(proxyRes.headers["content-type"] ?? "");
              const chunks: Buffer[] = [];

              proxyRes.on("data", (chunk: Buffer) => {
                chunks.push(chunk);
              });

              proxyRes.on("end", () => {
                let body = Buffer.concat(chunks);

                if (shouldRewriteContent(contentType)) {
                  const rewritten = rewriteTegContent(
                    body.toString("utf8"),
                    contentType,
                  );
                  body = Buffer.from(rewritten, "utf8");
                  proxyRes.headers["content-length"] = String(body.length);
                }

                res.writeHead(proxyRes.statusCode ?? 500, proxyRes.headers);
                res.end(body);
              });

              proxyRes.on("error", () => {
                res.writeHead(502);
                res.end("Bad gateway");
              });
            });
          },
        },
      },
    },
    build: {
      outDir: "dist",
      emptyOutDir: true,
    },
  };
});
