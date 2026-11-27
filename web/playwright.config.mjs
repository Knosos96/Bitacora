import { defineConfig } from "@playwright/test";

const baseURL = process.env.BASE_URL || "http://127.0.0.1:8001";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 180_000,
  expect: { timeout: 12_000 },
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    actionTimeout: 15_000,
    channel: process.env.PW_CHANNEL || "chrome",
    headless: process.env.PW_HEADLESS !== "false",
    viewport: { width: 1400, height: 900 },
    acceptDownloads: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "python -m uvicorn app.main:app --host 127.0.0.1 --port 8001",
    url: baseURL,
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
