# Cómo correr y verificar el proyecto

## Instalación

```bash
npm install
```

Instala todo el monorepo (workspaces `packages/*`, `apps/web`, `apps/mobile`)
desde la raíz con un único `npm install`.

## Web

```bash
npm run dev:web          # http://localhost:5173
npm run typecheck:web    # tsc --noEmit
npm run build:web        # typecheck + build de producción (Vite)
```

## Mobile (Expo)

```bash
npm run dev:mobile       # expo start (QR para Expo Go / simulador)
npm run typecheck:mobile # tsc --noEmit
```

Verificación local de bundling sin dispositivo/simulador (usa
`react-native-web` solo como humo de compilación, la plataforma real sigue
siendo iOS/Android):

```bash
cd apps/mobile
EXPO_OFFLINE=1 npx expo export -p web --output-dir /tmp/expo-web-export
```

(`EXPO_OFFLINE=1` evita que el CLI intente validar versiones de paquetes
contra la API de Expo, que puede no ser alcanzable según la red del
entorno; no afecta el resultado del bundling.)

## Pruebas e2e (Playwright) — solo `apps/web`

```bash
cd apps/web
npx playwright test               # corre todo: flujos + capturas responsive
npx playwright test e2e/flows.spec.ts        # solo los 3 flujos clave
npx playwright test e2e/responsive.spec.ts   # solo las capturas de breakpoints
```

`playwright.config.ts` levanta automáticamente `vite dev` en el puerto 5173
(`webServer`) si no está corriendo. Usa el Chromium preinstalado del
contenedor (`/opt/pw-browsers/chromium`) en vez de descargar uno nuevo.

### Qué cubre `e2e/flows.spec.ts`

1. **Alta de producto** — crea una figura nueva con una variante desde el
   catálogo y verifica que aparezca en la lista.
2. **Ajuste de inventario** — sube el stock de una variante existente y
   verifica el nuevo valor; además prueba que un ajuste que dejaría stock
   negativo se rechaza (`InsufficientStockError` propagado a la UI).
3. **Creación de pedido** — crea un pedido, verifica que aparezca en la
   lista y que el stock de la variante vendida se haya descontado
   correctamente en la vista de Inventario; además prueba que un pedido por
   más unidades que el stock disponible se rechaza.

### Qué cubre `e2e/responsive.spec.ts`

Recorre las 3 páginas (Catálogo, Inventario, Pedidos) en 3 breakpoints:

| Breakpoint | Ancho  |
|---|---|
| mobile  | 390px  |
| tablet  | 768px  |
| desktop | 1440px |

y guarda una captura de página completa en `docs/screenshots/` con el
patrón `<pagina>-<breakpoint>-<ancho>px.png` (ej.
`inventario-mobile-390px.png`). Esto es obligatorio para toda nueva feature
de UI — ver `CLAUDE.md`.

## Notas del entorno de este workspace

- El proyecto se desarrolló en un contenedor con salida HTTPS a través de un
  proxy con CA propia. Las fuentes de Google Fonts se cargan por red durante
  los tests; `playwright.config.ts` tiene `ignoreHTTPSErrors: true` para que
  el Chromium de test acepte el certificado del proxy. Esto es específico
  del entorno de desarrollo — en producción los navegadores de los usuarios
  no pasan por este proxy y no lo necesitan.
- Si `@playwright/test` se actualiza a una versión que espera una revisión
  de Chromium distinta a la preinstalada en `/opt/pw-browsers`, seguir
  usando `launchOptions.executablePath` en `playwright.config.ts` en vez de
  `npx playwright install` (ver `/root/.ccr/README.md` del contenedor).
