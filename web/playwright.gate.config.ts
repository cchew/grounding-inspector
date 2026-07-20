import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: "gate.e2e.spec.ts",
  use: {
    baseURL: "http://localhost:8888",
  },
  webServer: {
    command: "netlify dev",
    url: "http://localhost:8888",
    reuseExistingServer: false,
    timeout: 30000,
  },
});
