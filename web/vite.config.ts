import { readFileSync } from "node:fs";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const pkg = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf-8"));

export default defineConfig({
  plugins: [vue()],
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  // e2e*.spec.* are Playwright specs (see playwright.config.ts testMatch) and
  // must stay out of the vitest run -- the pattern is a prefix glob, not the
  // single e2e.spec.* filename, so a second spec file (e2e-live-check) can't
  // silently start failing collection under vitest.
  test: { environment: "happy-dom", globals: true, exclude: ["**/e2e*.spec.*", "**/node_modules/**"] },
});
