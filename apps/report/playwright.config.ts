import { defineConfig, devices } from "@playwright/test";

/**
 * E2E real (navegador Chromium de verdad) contra el gate del reporte. Levanta la app
 * Next real con una contraseña conocida y usa el Chromium preinstalado del entorno
 * (no descarga navegador). Ver README para correr localmente.
 */
const PORT = 3020;
const PASSWORD = "e2e-pass-123";
const CHROME =
  process.env.PW_CHROME ||
  "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "off",
    launchOptions: { executablePath: CHROME },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npx next dev -p ${PORT}`,
    url: `http://localhost:${PORT}/login`,
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
    env: {
      REPORT_PASSWORD: PASSWORD,
      REPORT_SECRET: "e2e-secret-do-not-use-in-prod",
    },
  },
});
