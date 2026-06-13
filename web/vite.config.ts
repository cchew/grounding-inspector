import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  test: { environment: "happy-dom", globals: true, exclude: ["**/e2e.spec.*", "**/node_modules/**"] },
});
