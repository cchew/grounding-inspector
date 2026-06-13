import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: "e2e.spec.ts",
  use: {
    baseURL: "http://localhost:3000",
  },
  webServer: {
    command: "npm run serve",
    url: "http://localhost:3000/api/fixtures",
    reuseExistingServer: false,
    timeout: 15000,
  },
});
