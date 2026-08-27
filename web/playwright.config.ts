import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: "*.spec.ts",
  use: {
    baseURL: "http://localhost:3100",
  },
  webServer: {
    command: "PORT=3100 npm run serve",
    url: "http://localhost:3100/api/fixtures",
    reuseExistingServer: false,
    timeout: 15000,
  },
});
