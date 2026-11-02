import { defineConfig } from "astro/config";

// GitHub Pages 项目页部署在 /mingzhou/ 子路径下，
// 本地开发时用 base 也保持一致，避免"本地好、线上 404"。
export default defineConfig({
  site: "https://cloudzun.github.io",
  base: "/mingzhou",
  output: "static",
  build: { assets: "assets" },
  vite: { build: { assetsInlineLimit: 0 } }
});
