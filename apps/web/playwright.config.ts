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
    ignoreHTTPSErrors: true,
  },
  webServer: [
    {
      command: "npm run dev -- --port 5173 --strictPort",
      port: 5173,
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      // API REST real (services/octo-erp-agent) que consume la web — ver
      // src/api/ErpApiProvider.tsx y docs/decisions/007-rest-api-para-apps-web.md. Sin
      // COSMOS_ENDPOINT usa InMemoryRepository (mismos datos semilla que packages/shared).
      // AGENT_LLM_DISABLED=1: agent.spec.ts verifica texto exacto de las respuestas del
      // agente — un LLM real (decisión 010) parafrasea distinto cada vez, así que los e2e
      // corren contra el modo determinístico. Lo que importa para un e2e es que la UI
      // refleje el estado real del backend, no la redacción de un modelo no-determinístico
      // (eso se prueba aparte, a nivel de backend, en test_agent_chat_llm.py).
      command: "uv run uvicorn octo_erp_agent.http_app:asgi_app --host 127.0.0.1 --port 8000",
      cwd: "../../services/octo-erp-agent",
      port: 8000,
      reuseExistingServer: true,
      timeout: 60_000,
      env: { AGENT_LLM_DISABLED: "1" },
    },
  ],
});
