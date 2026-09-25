# CLAUDE.md — Octo ERP

ERP para venta de figuras impresas en 3D. Dos frontends (`apps/web` en
React, `apps/mobile` en Expo/React Native) que comparten dominio
(`packages/shared`) y design system (`packages/design-tokens`). Ver
`docs/architecture.md` para el detalle completo antes de tocar código.

## Reglas persistentes (aplican a toda sesión futura en este repo)

### 1. Design system como única fuente de estilos

- Todo color, tipografía, espaciado, radio o borde usado en `apps/web` o
  `apps/mobile` **tiene que venir** de
  `packages/design-tokens/src/tokens.json` (vía `tokens.css` en web o
  `theme.ts` en mobile). Nunca un hex, `px` o `font-family` sueltos en un
  componente o estilo.
- Si hace falta algo que el design system no cubre, se agrega explícitamente
  a `tokens.json` (y se documenta por qué en `docs/design-system.md`), nunca
  se inventa un valor ad-hoc dentro de un componente.
- Los componentes de interfaz nuevos van en
  `apps/web/src/design-system/` o `apps/mobile/src/design-system/`,
  siguiendo la especificación visual del design system original (esquinas
  rectas salvo `radius-sm` en controles, sin sombras, bordes `hairline` en
  vez de elevación). Ver `docs/design-system.md` para la tabla de qué
  componentes existen y por qué.

### 2. Toda feature nueva se verifica con Playwright antes de darse por terminada

- Cualquier cambio de UI/flujo en `apps/web` necesita al menos un test en
  `apps/web/e2e/` que ejercite el flujo real (no solo que la página cargue).
  Correr `npx playwright test` desde `apps/web` y que pase en verde es
  condición para considerar la feature terminada — no alcanza con que
  compile o con revisión visual manual.
- Ver `docs/testing.md` para cómo correr las pruebas y qué cubren las
  existentes (alta de producto, ajuste de inventario, creación de pedido,
  y sus validaciones negativas).
- Para `apps/mobile`, ante la ausencia de Playwright/simulador en muchos
  entornos, la verificación mínima es `tsc --noEmit` sin errores; si el
  cambio es de bundling/estructura, verificar además con
  `EXPO_OFFLINE=1 npx expo export -p web` (ver `docs/testing.md`).

### 3. Las capturas de Playwright van siempre a `/docs/screenshots/`

- Nombre descriptivo: `<pagina>-<breakpoint>-<ancho>px.png` (ej.
  `inventario-mobile-390px.png`, `pedidos-desktop-1440px.png`).
- Toda feature de UI nueva o modificada se verifica en al menos 3
  breakpoints: mobile (390px), tablet (768px), desktop (1440px) — extender
  `apps/web/e2e/responsive.spec.ts` con la página/estado nuevo en vez de
  crear un mecanismo de captura paralelo.

### 4. Toda decisión relevante se documenta en `/docs/` a medida que se avanza

- Decisiones de arquitectura, diseño o trade-offs (por qué esa estructura,
  qué se dejó afuera y por qué, qué alternativa se descartó) van como un
  archivo numerado en `docs/decisions/NNN-titulo.md`, siguiendo el formato
  de los existentes (contexto → decisión → por qué → trade-offs aceptados).
- `docs/status.md` se actualiza en la misma sesión en que se completa o se
  deja pendiente algo relevante: qué se hizo, qué falta, cómo retomarlo.
  No se abandona una sesión de trabajo con `docs/status.md` desactualizado.

## Mapa rápido

- `docs/architecture.md` — estructura del monorepo y por qué.
- `docs/design-system.md` — traducción de tokens/componentes a código.
- `docs/decisions/` — decisiones puntuales con su trade-off.
- `docs/status.md` — qué está hecho, qué falta, cómo retomar.
- `docs/testing.md` — cómo correr typecheck, build y Playwright.
- `docs/screenshots/` — capturas de Playwright (regla 3).
