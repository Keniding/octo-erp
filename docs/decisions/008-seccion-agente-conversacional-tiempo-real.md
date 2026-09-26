# 008 — Sección "Agente" en apps/web: chat conversacional con acciones reales y actualización en tiempo real

**Estado:** implementado y probado end-to-end (backend + frontend + tiempo real cross-tab).

## Contexto

Con la API REST real ya en producción (decisión 007) y el dominio/MCP ya probados
(decisiones 004/006), el siguiente paso pedido explícitamente fue: una sección dentro de
`apps/web`, construida con los componentes del design system ya integrados, donde viva un
agente que ayude a gestionar el ERP de forma conversacional, pueda ejecutar acciones reales,
y que el resto de la web se actualice en tiempo real con esos cambios a nivel de base de
datos.

## Decisión

### 1. El "cerebro" del chat es hoy un intérprete de comandos, no un LLM — y se dice así, explícitamente

`services/octo-erp-agent/src/octo_erp_agent/agent_chat.py` reconoce un set fijo de
patrones en español (`catálogo`, `stock de <SKU>`, `stock bajo`, `pedido <SKU> x<N> para
<CLIENTE>`, `ajustar <SKU> <+/-N> [motivo]`) y llama a las mismas funciones de
`domain/service.py` que ya usan `mcp_server.py` (protocolo MCP, para Foundry) y
`rest_api.py` (REST, para el resto de la web) — ninguna regla de negocio nueva, ninguna
tercera copia de "nunca vender más stock del disponible".

Esto **no** es el agente de IA final: es el placeholder honesto hasta que Azure AI Foundry
esté desplegado (pendiente: `oraculo/docs/10-especificacion-2-agente-octo-erp.md`, sección
10.9, todavía bloqueada por el proyecto de ejemplo del usuario). El reemplazo, cuando pase,
es *solo* este archivo — la ruta HTTP (`POST /api/agent/chat`), su contrato de respuesta
(`{"reply": str, "action": dict | null}`) y el frontend (`AgentPage.tsx`) no cambian, porque
ya hablan con las mismas funciones de dominio que usará Foundry vía MCP.

Se prefirió esto a fingir una integración de LLM sin credenciales reales disponibles en el
entorno de desarrollo de esta sesión — mejor un motor simple, honesto sobre sus límites y
100% probado, que una promesa de "IA" que en los hechos sería la misma lógica de patrones
pero sin decirlo.

### 2. Tiempo real = polling, no WebSockets/SSE — decisión de infraestructura, no de gusto

`ErpApiProvider` ahora refresca `/api/state` cada 4 segundos en segundo plano
(`POLL_INTERVAL_MS`), además de refrescar de inmediato tras cada acción propia. Se descartó
explícitamente SSE/WebSockets: `oraculo/docs/04-protocolo-mcp.md` (sección 4.4) ya
documentó, en producción real, que una conexión HTTP abierta y no cerrada por el cliente en
Azure Functions Consumption se queda colgada hasta que la plataforma la mata por timeout —
el mismo problema volvería a aparecer acá. Agregar Azure Web PubSub/SignalR resolvería esto
"bien", pero introduce un recurso de pago y complejidad nueva, en contra del objetivo de
"$0 en idle" que ya gobierna el resto de esta infraestructura (decisión 006). Polling cada
4s es la opción que funciona de verdad con lo que ya existe.

### 3. La sección se construyó 100% con el design system existente

`AgentPage.tsx` reutiliza `Card`/`Callout`/`GridPaper`/`Input`/`Button`/`Label` de
`apps/web/src/design-system` — cero valores de color/tipografía/espaciado nuevos (regla 1
de `CLAUDE.md`). El único CSS nuevo (`agent-page.css`) define layout (burbujas de chat,
scroll del transcript), no estilo — todo color/borde/radio ahí referencia las mismas
variables (`--surface-raised`, `--rule`, `--accent`, etc.) que ya usa el resto de la app.

## Verificado corriendo de verdad (no solo "debería funcionar")

- **Backend**: 15 tests nuevos en `services/octo-erp-agent/tests/test_agent_chat.py` — cada
  comando, sus variantes de mayúsculas/espaciado, y los casos de rechazo (SKU inexistente,
  stock insuficiente) verificados contra `InMemoryRepository` real (no mocks). Total del
  paquete: 45 tests pasando + 4 de integración contra Cosmos DB real que se saltan sin
  `COSMOS_ENDPOINT` (esperado en este entorno sin credenciales de Azure).
- **Frontend**: 5 tests nuevos en `apps/web/e2e/agent.spec.ts`, contra el backend Python real
  (no un mock) vía los dos `webServer` de `playwright.config.ts`. El más importante:
  **"una acción del agente se refleja en tiempo real en otra pestaña, sin recargar"** — abre
  dos páginas de Playwright en el mismo contexto, ejecuta una acción de ajuste de stock
  *solo* en la pestaña del agente, y confirma (con un timeout mayor al intervalo de polling)
  que la pestaña de Inventario — que nunca navegó ni se tocó — refleja el cambio sola. Esta
  es la prueba real de "se actualiza en tiempo real la web", no una afirmación sin verificar.
- Se encontró y arregló un bug de aislamiento de tests real en el camino:
  `flows.spec.ts` tenía hardcodeado `toHaveText("2")` para `var-dragon-resina` asumiendo que
  nada más tocaría esa variante — con `agent.spec.ts` corriendo antes (orden alfabético) y
  mutando esa misma variante, el test empezó a fallar. Se corrigió para leer el stock actual
  antes de actuar, mismo patrón que ya usaba el test de al lado (creación de pedido) por el
  mismo motivo, documentado en la decisión 007.
- Capturas de los 3 breakpoints estándar del proyecto en `docs/screenshots/agente-*.png`
  (regla 3 de `CLAUDE.md`) — se encontró y arregló un problema de layout real en mobile (el
  input de mensaje y el botón "Enviar" quedaban apretados en una sola fila angosta);
  corregido apilándolos verticalmente por debajo de 640px, mismo criterio que ya estableció
  la decisión 003 para los formularios multi-fila.

## Trade-offs aceptados

- **El "agente" no entiende lenguaje libre** — solo los patrones documentados en
  `agent_chat.py`. Cualquier otra cosa devuelve un mensaje de ayuda explícito, nunca una
  respuesta inventada ni un error silencioso. Aceptado como el estado intermedio honesto
  hasta que Foundry esté conectado.
- **Polling cada 4s, no instantáneo**: un cambio hecho en otra pestaña puede tardar hasta 4
  segundos en aparecer. Aceptado por las razones de infraestructura de la sección 2 — no es
  un descuido, es la opción correcta dado el plan Consumption de Azure Functions.
- **Sin autenticación en `/api/agent/chat`**, igual que el resto de `/api/*` (ver "Pendiente"
  en la decisión 007) — mismo resource group de dev/test, mismo alcance ya aceptado.
