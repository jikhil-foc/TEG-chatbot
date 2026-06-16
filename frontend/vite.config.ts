import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

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
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: "dist",
      emptyOutDir: true,
    },
  };
});
