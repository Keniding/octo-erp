# Estado del proyecto

Última actualización: 2026-09-26.

## Agente conversacional con LLM real (nuevo — decisión 010)

- La sección "Agente" de `apps/web` ya no es un intérprete de comandos por regex (decisión
  008) como único camino — ahora usa un LLM real (`gpt-5.4-nano`, Azure AI Foundry, recurso
  dedicado `octo-erp-ai` en `rg-octo-erp-dev`, separado del de `oraculo`), con tool-calling
  ejecutado *vía protocolo MCP real* (cliente MCP en memoria contra el mismo servidor MCP
  que expone `/mcp`) — nunca llamadas directas a Python en paralelo. Auth 100% Entra ID
  (Managed Identity / `az login`, sin keys).
- **Sin fallback silencioso si el LLM falla** — pedido explícito del usuario, ver decisión
  010: un error visible en vez de una respuesta que coincide por casualidad con un patrón
  fijo y aparenta que el modelo entendió.
- Probado contra Azure real: creación de pedidos y consultas en lenguaje natural sin SKU
  exacto (algo que el intérprete por regex anterior no podía resolver). 18 tests reales
  (14 en modo sin LLM + 4 contra el LLM real, opt-in con `RUN_LLM_INTEGRATION_TESTS=1`).
- Dos tools MCP nuevas agregadas: `adjust_material_stock`, `list_orders`, más
  `find_variant_by_sku` expuesta como tool (ya existía en el dominio).

## Agente de IA + MCP + Cosmos DB (`services/octo-erp-agent/`)

- **Decisión tomada**: Cosmos DB es la única fuente de verdad de datos de negocio; el
  frontend cachea (TanStack Query) pero nunca es la fuente — ver
  [decisión 004](decisions/004-agente-ia-mcp-cosmosdb.md) y
  [decisión 005](decisions/005-cache-frontend-vs-fuente-de-verdad.md).
- **Implementado y probado (24/24 tests reales, no solo especificado)**: dominio de negocio
  en Python (`domain/service.py`, puerto 1:1 de `packages/shared/src/store.ts`) + servidor
  MCP custom (`mcp_server.py`, mismo patrón que `oraculo/mcp_server.py`) + repositorio en
  memoria para tests. Incluye un test end-to-end real sobre el protocolo MCP (cliente MCP
  oficial contra un servidor HTTP real, no mocks) — ver `services/octo-erp-agent/README.md`.
- **`CosmosRepository` verificado contra una cuenta real de Azure** (ya no es solo código
  escrito contra la API del SDK): `rg-octo-erp-dev` (eastus) tiene una cuenta de Cosmos DB
  Serverless real con los 5 containers del esquema, y
  `tests/test_cosmos_integration.py` (4 tests, round-trip real: producto, variante+stock,
  material+stock, pedido+movimiento) pasa en verde contra ella, autenticado por RBAC de
  datos de Entra ID (sin keys — la cuenta tiene `disableLocalAuth: true`). Ver
  [decisión 006](decisions/006-ci-cd-azure-oidc.md) para el detalle completo.
- **CI/CD en GitHub Actions, con OIDC federado (sin secrets de larga vida), corriendo en
  verde de punta a punta**: `.github/workflows/octo-erp-agent-ci.yml` (tests unitarios en
  cada push/PR + el test de integración contra Cosmos real) y `octo-erp-agent-cd.yml`
  (deploy del Bicep + publish de `function_app.py`). Las dos asignaciones de rol que el
  clasificador de permisos de Claude Code bloqueó como "otorgar permisos" ya las corrió el
  usuario (ver decisión 006) — quedan documentados ahí dos bugs reales que se encontraron y
  arreglaron corriendo los workflows de verdad (formato de subject del OIDC, región del
  deploy).
- **API REST para `apps/web` (nuevo, decisión 007)**: `rest_api.py` + `http_app.py` exponen
  `/api/*` en el mismo Function App que el MCP, reusando `domain/service.py`. `apps/web` ya
  no usa el store en memoria de `packages/shared` — tiene un `ErpApiProvider` propio que le
  pega a esa API.
- **Desplegado y funcionando en Azure real, verificado de punta a punta**:
  API/MCP en `https://octo-erp-inc.azurewebsites.net`, web real en
  `https://stoctoerpinc.z5.web.core.windows.net/` (Azure Storage static website). Un pedido
  creado a mano vía `curl` contra `/api/orders` se guardó de verdad en Cosmos DB y descontó
  stock — no es una demo, es la cosa funcionando. El deploy tardó mucho más de lo esperado
  por un problema real de plataforma (ver decisión 007, "El deploy no era
  reproducible/determinístico"): el sync-trigger de Azure para Function Apps Python en
  Consumption resultó intermitentemente inestable en esta suscripción — no por código, sino
  porque **cambiar un app setting justo antes de redesplegar dispara la falla**; redesplegar
  solo código es confiable. Se resolvió sacando el origen de CORS del sitio estático de un
  app setting y hardcodeándolo en el código. En el camino también se encontraron y
  arreglaron 3 bugs reales de CI/CD (detalle en decisión 007): un `executablePath` de
  Chromium de Linux hardcodeado en `playwright.config.ts` de una sesión anterior en sandbox,
  un test con estado hardcodeado que no toleraba que el backend ahora persiste entre tests,
  y que `Azure/functions-action@v1` con RBAC/OIDC contra Linux Consumption no corre ningún
  build remoto por defecto.
- **Sección "Agente" en `apps/web` (nuevo, decisión 008)**: página `/agente`, construida 100%
  con el design system existente, con un chat que ejecuta acciones reales (crear pedidos,
  ajustar stock, consultar catálogo/stock bajo) contra las mismas funciones de dominio que ya
  usan el MCP y la API REST. El "cerebro" hoy es un intérprete de comandos (no un LLM
  todavía — honesto y documentado así, ver decisión 008), pensado como el punto exacto donde
  Foundry se conecta después sin tocar el resto del código. `ErpApiProvider` ahora hace
  polling cada 4s además de refrescar tras cada acción propia, así que un cambio hecho por el
  agente (o por cualquier otro cliente) aparece solo, sin recargar — **verificado con un test
  de Playwright real que abre dos pestañas y confirma la propagación sin que la segunda
  navegue nunca**. 20 tests nuevos (15 backend + 5 e2e), suite completa en verde (45+4
  backend, 28 e2e).
- **CD de `apps/web` (nuevo, decisión 009) — bloqueado en un role assignment**: el sitio
  público seguía sin la sección "Agente" después de la decisión 008 porque
  `octo-erp-agent-cd.yml` nunca desplegó el frontend — solo la API/MCP. Se agregó
  `apps-web-cd.yml` (build de `apps/web` + `az storage blob upload-batch` al contenedor
  `$web` de `stoctoerpinc`, autenticado por OIDC). Probablemente necesita un role
  assignment nuevo (`Storage Blob Data Contributor` sobre `stoctoerpinc`) que el dueño de la
  cuenta tiene que correr — comando exacto en la decisión 009. También se encontró y
  arregló que `octo-erp-agent-ci.yml` nunca corría `test_rest_api.py` ni
  `test_agent_chat.py` (lista de archivos a mano, desactualizada) a pesar de verse en verde.
- **Pendiente**: `apps/mobile` sigue sin conectarse a Azure (fuera de alcance de esta
  sesión, ver decisión 007); auth Entra ID/Easy Auth de cara al agente/Foundry; conectar el
  agente a un LLM real (Azure AI Foundry) en vez del intérprete de comandos actual; el role
  assignment de la decisión 009 (bloqueante para que el sitio público se actualice solo); y
  el proyecto de ejemplo del usuario para el mecanismo exacto de esa auth. Especificación
  completa en `oraculo/docs/10-especificacion-2-agente-octo-erp.md`.

## Hecho

- Fix de responsividad en los formularios multi-fila (`ProductForm`,
  `OrderForm` en `apps/web`): el botón "+ Agregar variante"/"+ Agregar
  artículo" ya no se estiraba a todo el ancho del contenedor, y la grilla
  de campos de cada variante/artículo pasó de saltar de 1 a 6 columnas
  fijas en 768px a una grilla `auto-fit` que se adapta a tablet y desktop
  sin comprimir los campos. Ver
  `docs/decisions/003-formularios-responsive.md`. Verificado con capturas
  de Playwright del formulario abierto en los 3 breakpoints
  (`catalogo-formulario-*`, `pedidos-formulario-*` en `docs/screenshots/`).

- Monorepo con npm workspaces: `packages/design-tokens`, `packages/shared`,
  `apps/web`, `apps/mobile`.
- Design system del workspace leído y traducido a `tokens.json` / `tokens.css`
  / `theme.ts`; ningún color/tipografía/espaciado inventado fuera de esos
  tokens (ver `docs/design-system.md`).
- Dominio compartido (`packages/shared`): tipos, store de zustand, datos
  semilla de figuras 3D (samurái, mecha, dragón), reglas de negocio
  (validación de stock al ajustar inventario y al crear pedidos).
- **Web** (`apps/web`): catálogo con alta de figuras (multi-variante),
  inventario con ajuste de stock de variantes y de materiales/filamento,
  pedidos con alta y descuento automático de stock. Tipografía real del
  design system cargada vía Google Fonts. `npm run build:web` compila sin
  errores. Fuente de datos: la API REST real de `services/octo-erp-agent`
  (ver decisión 007), no más el store en memoria.
- **Mobile** (`apps/mobile`, Expo): las mismas tres pantallas, mismo dominio
  compartido, componentes de interfaz propios en React Native siguiendo la
  misma especificación visual. `tsc --noEmit` sin errores y bundling
  verificado con `expo export -p web` (Metro resuelve correctamente los
  paquetes de workspace vía `metro.config.js`).
- Pruebas e2e con Playwright en `apps/web` (20 tests, todos en verde, contra
  el backend real vía `VITE_API_BASE_URL` — ver decisión 007): 3 flujos
  clave (alta de producto, ajuste de inventario, creación de pedido) más
  sus casos de validación negativa, y capturas de responsividad (3 páginas
  × 3 breakpoints + 2 formularios × 3 breakpoints) guardadas en
  `docs/screenshots/`. `playwright.config.ts` levanta Vite y el backend
  Python juntos (`webServer` como array).
- Documentación en `docs/`: arquitectura, uso del design system, decisiones
  con trade-offs, esta página de estado, y cómo correr todo.
- `CLAUDE.md` en la raíz con las reglas persistentes pedidas.

## Falta / próximos pasos sugeridos

- **Backend real para `apps/mobile`**: `apps/web` ya habla con la API real
  (decisión 007); `apps/mobile` sigue sobre `packages/shared/src/store.ts`
  en memoria (ver `docs/decisions/001-persistencia-en-memoria.md`),
  deliberadamente fuera de alcance de esta sesión.
- **GridPaper en mobile**: no reproduce la cuadrícula de 19px del design
  system (requeriría SVG). Ver `docs/design-system.md`.
- **ProductForm en mobile**: solo admite una variante por alta (en web
  admite varias). Ver `docs/decisions/002-navegacion-y-formularios.md`.
- **Navegación mobile**: switch de pantalla propio en vez de
  `react-navigation`; suficiente para 3 módulos hermanos, a revisar si se
  agregan pantallas de detalle o deep links.
- **Verificación e2e de mobile**: no hay pruebas automatizadas para la app
  Expo (Playwright solo cubre la web, tal como se pidió). El bundling se
  verificó manualmente con `expo export -p web`; para pruebas end-to-end
  reales en mobile habría que evaluar Detox o Maestro sobre un
  simulador/dispositivo, que este entorno no tiene disponible.
- **Autenticación / multiusuario**: no implementado, no estaba en el
  alcance pedido.
- **Tema Tinta (oscuro) y Alto contraste**: los tokens ya están cargados en
  `tokens.json`/`tokens.css` para el tema oscuro (`data-theme="dark"`) y se
  aplica automáticamente en mobile según `useColorScheme`, pero la web no
  tiene todavía un selector de tema visible ni el tema de Alto contraste
  implementado.

## Cómo retomar

1. Leer `docs/architecture.md` para entender la estructura y el porqué de
   cada decisión.
2. Leer `docs/design-system.md` antes de tocar cualquier estilo.
3. `npm install` en la raíz, luego `docs/testing.md` para correr cada app y
   las pruebas.
4. Cualquier feature nueva pasa por Playwright antes de darse por terminada
   (regla en `CLAUDE.md`).
