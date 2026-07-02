import { existsSync } from "node:fs";
import { defineConfig, devices } from "@playwright/test";

/**
 * E2E real (navegador Chromium de verdad) contra el gate del reporte. Levanta la app
 * Next real con una contraseña conocida.
 * - En este entorno usa el Chromium preinstalado (executablePath), sin descargar nada.
 * - En CI (donde no existe ese binario) usa el Chromium que instala `playwright install`.
 */
const PORT = 3020;
const PASSWORD = "e2e-pass-123";
const LOCAL_CHROME =
  process.env.PW_CHROME || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const useLocalChrome = !!LOCAL_CHROME && existsSync(LOCAL_CHROME);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "off",
    launchOptions: useLocalChrome ? { executablePath: LOCAL_CHROME } : {},
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
