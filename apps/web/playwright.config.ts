import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
    // El contenedor de esta sesión enruta HTTPS por un proxy con CA propia
    // (ver /root/.ccr/README.md); Chromium no la valida por defecto, así que
    // ignoramos errores de certificado solo para poder cargar Google Fonts en test.
    ignoreHTTPSErrors: true,
    launchOptions: {
      executablePath: "/opt/pw-browsers/chromium",
    },
  },
  webServer: {
    command: "npm run dev -- --port 5173 --strictPort",
    port: 5173,
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
