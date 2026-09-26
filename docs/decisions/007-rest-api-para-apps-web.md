# 007 — API REST en el mismo Function App para que apps/web hable con lo desplegado en Azure

**Estado:** implementado y funcionando en Azure real. URL actual:
**`https://octo-erp-inc.azurewebsites.net`** (MCP en `/mcp`, REST en `/api/*`). Web real
desplegada en **`https://stoctoerpinc.z5.web.core.windows.net/`** (Azure Storage static
website), apuntando a esa API. Ver "El deploy no era reproducible/determinístico" más abajo
para la historia completa de por qué la URL cambió varias veces durante la sesión.

## Contexto

Hasta esta sesión, `apps/web` seguía 100% sobre `packages/shared/src/store.ts` (zustand, en
memoria) — cero código que hablara con Azure, a pesar de que `services/octo-erp-agent` ya
tenía un Cosmos DB real desplegado y probado (decisión 006). La decisión 005 ya marcaba esto
como trabajo futuro ("no es una tarea de esta sesión"); esta sesión sí lo era.

El servidor MCP (`mcp_server.py`) no sirve para esto directamente: es protocolo MCP
(JSON-RPC sobre streamable-http), pensado para que un agente de IA lo llame vía un cliente
MCP, no para que un browser le pegue con `fetch`.

## Decisión

**API REST nueva, en el mismo proceso y el mismo Function App que el MCP** (alternativa
elegida sobre un servicio Node/Express separado): `rest_api.py` define las rutas HTTP
(`/api/state`, `/api/products`, `/api/variants/{id}/stock-adjustments`,
`/api/materials/{id}/stock-adjustments`, `/api/orders`, `/api/orders/{id}/status`,
`/api/movements`), todas llamando a `domain/service.py` — exactamente las mismas funciones
que ya usa `mcp_server.py`, contra el mismo repositorio (`http_app.py` combina ambos en un
solo ASGI app, compartiendo la instancia de `mcp_server.repo`).

`apps/web` se conecta vía un `ErpApiProvider` (`apps/web/src/api/ErpApiProvider.tsx`) — un
Context de React que reemplaza a `useErpStore` como fuente de datos, pero **no toca**
`packages/shared/src/store.ts`: ese store sigue existiendo intacto porque `apps/mobile`
todavía lo usa (ver "Trade-offs aceptados"). Los 5 puntos de uso en `apps/web`
(`CatalogPage`, `ProductForm`, `InventoryPage`, `OrderForm`, `OrdersPage`) se migraron de
`useErpStore` a `useErp()`, y sus `handleSubmit`/`handleAdjust*` pasaron a ser `async`.

## Por qué

- **Mismo Function App que el MCP** en vez de un servicio separado: reusa
  `domain/service.py` (ya probado, 20 tests) y el mismo repositorio/conexión a Cosmos DB, sin
  reimplementar la regla "nunca vender más stock del disponible" una segunda vez en otro
  stack — justo la duplicación que las decisiones 004/005 querían evitar.
- **No tocar `packages/shared/src/store.ts`**: cambiar su firma (de sync a async) rompería
  `apps/mobile`, que no estaba en el alcance pedido. Un Context nuevo en `apps/web`, con los
  mismos tipos de `@octo-erp/shared` pero su propia fuente de datos, deja `apps/mobile`
  exactamente como estaba (verificado: no se tocó ningún archivo de `apps/mobile`).
- **`VITE_API_BASE_URL` configurable** (`.env` con default `http://localhost:8000`) en vez
  de una URL hardcodeada: permite correr contra el backend local (default, para dev/e2e) o
  contra lo desplegado en Azure sin tocar código, solo con una variable de entorno al
  levantar Vite.

## Verificado corriendo de verdad (no solo "debería funcionar")

1. **Local, contra el backend Python real** (no un mock): `playwright.config.ts` ahora
   levanta dos `webServer` — Vite (5173) y `uvicorn octo_erp_agent.http_app:asgi_app` (8000,
   `services/octo-erp-agent`). Los 20 tests de `apps/web/e2e/` (5 flujos + 15 capturas
   responsive) pasan en verde contra ese backend real.
   - Se encontró y arregló un bug real de aislamiento de tests: con un store en memoria
     *por pestaña*, cada test partía de datos semilla frescos; con un backend de servidor
     *persistente entre tests*, el ajuste de stock de un test se acumulaba sobre el
     siguiente. `flows.spec.ts` tenía hardcodeado "14 → 12" en vez de leer el stock real
     antes de actuar (como ya hacía el test de al lado) — corregido para leer el valor
     actual, el patrón correcto contra un backend con estado real.
   - Se encontró y arregló `playwright.config.ts`: tenía un `executablePath` de Chromium de
     Linux (`/opt/pw-browsers/chromium`) de una sesión anterior en sandbox cloud — rompía
     todo en esta máquina Windows. Quitado; Playwright usa su propio Chromium cacheado.
2. **Deploy real a Azure encontró un bug real de CI/CD** (ver commit correspondiente):
   `Azure/functions-action@v1`, autenticado por RBAC/OIDC (no publish profile) contra un
   Function App Linux Consumption, usa el modo "Run From Package" y **no corre ningún build
   remoto** — el primer deploy subió el código fuente sin ninguna dependencia instalada
   (`mcp`, `azure-cosmos`, `starlette`, etc. faltaban), por eso la app no arrancaba
   (`/mcp` devolvía 404 en vez de 405, cero funciones indexadas). Corregido instalando las
   dependencias en el runner antes de empaquetar
   (`pip install --target="./.python_packages/lib/site-packages" -r requirements.txt`) —
   patrón oficial de Microsoft para Python + RBAC + Linux Consumption.
3. **Contra la cuenta real de Azure** (`https://octo-erp-hrhdi4.azurewebsites.net`), sembrada
   con `scripts/seed_cosmos.py`: `npx playwright test` con
   `VITE_API_BASE_URL=https://octo-erp-hrhdi4.azurewebsites.net` — mismo resultado en verde,
   navegador real → Vite → HTTP real → Function App real → Cosmos DB real.
4. **Causa real detrás de una racha larga de "sync trigger" fallidos** (después del punto
   2, con la app ya funcionando una vez): un cambio de infra posterior (agregar
   `CORS_ALLOWED_ORIGINS`) dejó la app sin responder, y **cuatro** mecanismos de deploy
   distintos fallaron igual contra ella (`Azure/functions-action@v1`, `az functionapp
   deploy`/OneDeploy, `az functionapp deployment source config-zip`, y `func azure
   functionapp publish`) — incluso recreando la Function App desde cero. Eso descartó que
   fuera el mecanismo de deploy o un estado corrupto puntual. La causa real:
   `azure-functions` en `requirements.txt`/`pyproject.toml` no tenía techo de versión y
   resolvía a `2.x`, que requiere Python ≥3.13 — pero el Function App corre `PYTHON|3.12`
   (ver `infra/main.bicep`). El worker de Python nunca llegaba a arrancar, así que el host
   no podía ni responder al sync trigger. **`oraculo/infra/README.md` ya documentaba
   exactamente este problema** (en la dirección opuesta: probaron `PYTHON|3.13` y les dio
   "503 persistente", fijaron `azure-functions<2.0.0` + `PYTHON|3.12`) — no se consultó esa
   referencia a tiempo, así que se perdió ~1 hora reintentando mecanismos de deploy en vez
   de mirar la causa real. Fijado con el mismo techo de versión
   (`azure-functions>=1.21.0,<2.0.0`).

## El deploy no era reproducible/determinístico — la causa real final

Después del punto 4 (fix de versión de `azure-functions`), el deploy siguió fallando de
forma intermitente durante horas — no por ese bug ni por ningún otro bug de código. Se
probó, en orden, y se descartó cada hipótesis con evidencia real (no supuesta):

- **Región** (`eastus` → `westus2`): un Function App trivial (`hello world`) funcionaba al
  instante en cualquier región; el proyecto real fallaba igual en ambas. Descartado.
- **Estado corrupto del recurso**: se borró y recreó la Function App, después también el
  Storage Account — mismo error exacto. Descartado.
- **Nombre del recurso "maldito"**: un nombre nunca usado antes funcionaba al instante con
  el código real completo (REST + MCP + Cosmos) — pero el MISMO nombre, en un intento
  posterior, volvía a fallar. Esto llevó a la hipótesis correcta.
- **Mecanismo de deploy**: `Azure/functions-action@v1`, `az functionapp deploy`
  (OneDeploy), `az functionapp deployment source config-zip` y `func azure functionapp
  publish` fallaban todos igual contra un nombre ya tocado. Descartado como causa única.
- **Rate limiting de Azure**: tras ~25 intentos de sync-trigger en la sesión, un intento
  devolvió explícitamente `TooManyRequests` — real, pero un intento posterior (tras 10 min
  de enfriamiento) volvió a fallar con `BadRequest`, así que no explicaba todo.

**El patrón real, confirmado con un experimento incremental controlado** (desplegar
funcionalidad de a una pieza, mismo patrón que usa `oraculo`, sobre un recurso nuevo
`octo-erp-inc`): agregar código nuevo y redesplegar es **confiable** (5/5 éxitos
instantáneos: mínimo → +Cosmos → +API REST → revertir CORS → +CORS hardcodeado en código).
**Cambiar un app setting (`az functionapp config appsettings set`) y redesplegar justo
después es lo que falla intermitentemente** (3/3 fallos exactos al tocar
`CORS_ALLOWED_ORIGINS` como app setting, incluso solo, incluso con la config revertida
después). La solución fue simplemente **no depender de un app setting para el origen de
CORS del sitio estático** — se hardcodeó como default en el propio código
(`http_app.py`, `_DEFAULT_CORS_ORIGINS`), así el deploy que lo aplica es un cambio de
código (confiable), no un cambio de config (inestable).

No queda explicado el mecanismo exacto de por qué un cambio de app setting seguido de un
redeploy dispara esto en la plataforma de Azure para esta suscripción — quedó como una regla
empírica probada, no como una causa de bajo nivel identificada. Si hay que agregar un app
setting nuevo en el futuro: cambiarlo, esperar, y **no** asumir que el próximo deploy va a
funcionar al primer intento.

## Pendiente / trade-offs aceptados

- **`apps/mobile` sigue sin conectarse a Azure** — sigue sobre `packages/shared/src/store.ts`
  en memoria, deliberadamente fuera de alcance de esta sesión (ver "Por qué"). Migrarlo
  necesitaría el mismo patrón (`useErp()` propio para mobile) o, mejor, extraer
  `ErpApiProvider` a algo compartible entre web y mobile si se decide hacerlo después.
- **Sin autenticación en `/api/*` todavía**: cualquiera que llegue a la URL de la Function
  App puede leer/mutar datos. Aceptado porque es un resource group de dev/test
  (`rg-octo-erp-dev`) y el alcance pedido era "que funcione de punta a punta", no
  productizarlo — la protección real (Entra ID/Easy Auth) es la misma pendiente que ya
  documentaba `mcp_server.py` para `/mcp`.
- **CORS abierto solo a `localhost:5173`/`4173` por default** (`CORS_ALLOWED_ORIGINS`): el
  día que `apps/web` se despliegue en una URL real, hay que agregar esa URL a esa variable
  de entorno en la Function App — no pasa automáticamente.
