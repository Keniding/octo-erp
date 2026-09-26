# Estado del proyecto

Última actualización: 2026-09-26.

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
  pega a esa API. **Verificado con Playwright de punta a punta contra la cuenta real de
  Azure** (no solo local): `https://octo-erp-hrhdi4.azurewebsites.net`, sembrada con
  `scripts/seed_cosmos.py`. En el camino se encontraron y arreglaron 3 bugs reales: un
  `executablePath` de Chromium de Linux hardcodeado en `playwright.config.ts` de una sesión
  anterior en sandbox, un test con estado hardcodeado que no toleraba que el backend ahora
  persiste entre tests, y — el más importante — que `Azure/functions-action@v1` con
  RBAC/OIDC contra Linux Consumption no corre ningún build remoto y desplegaba código sin
  ninguna dependencia instalada (arreglado instalando en el runner antes de empaquetar).
- **Pendiente**: `apps/mobile` sigue sin conectarse a Azure (fuera de alcance de esta
  sesión, ver decisión 007); auth Entra ID/Easy Auth de cara al agente/Foundry; y el
  proyecto de ejemplo del usuario para el mecanismo exacto de esa auth. Especificación
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
