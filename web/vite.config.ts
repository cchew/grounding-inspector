import { readFileSync } from "node:fs";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const pkg = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf-8"));

export default defineConfig({
  plugins: [vue()],
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  test: { environment: "happy-dom", globals: true, exclude: ["**/e2e.spec.*", "**/gate.e2e.spec.*", "**/node_modules/**"] },
});
