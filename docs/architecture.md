# Arquitectura — Octo ERP

## Objetivo

ERP para la venta de figuras impresas en 3D, con dos frontends (web y móvil)
que comparten el mismo dominio de negocio y el mismo design system.

## Estructura del monorepo

```
octo-erp/
├── packages/
│   ├── design-tokens/     # Fuente única de verdad de estilo (colores, tipografía,
│   │                       # espaciado, radios, bordes), como CSS vars (web) y objeto TS (RN)
│   └── shared/             # Dominio: tipos, store (zustand), datos semilla, lógica de negocio
├── apps/
│   ├── web/                 # React + Vite + react-router. Playwright para e2e.
│   └── mobile/               # Expo + React Native. Mismo dominio, componentes RN propios.
└── docs/
    ├── architecture.md      # este archivo
    ├── design-system.md     # cómo se tradujo el design system a código
    ├── decisions/            # decisiones puntuales con su trade-off
    ├── status.md             # qué está hecho, qué falta
    ├── testing.md            # cómo correr typecheck, build y Playwright
    └── screenshots/          # capturas de Playwright (ver testing.md)
```

Es un monorepo con **npm workspaces** (sin herramienta adicional tipo Turborepo,
Nx, etc. — no aporta valor al tamaño actual del proyecto). `packages/*` son
dependencias de workspace (`"@octo-erp/design-tokens": "*"`,
`"@octo-erp/shared": "*"`) que Vite y Metro resuelven directamente contra el
código fuente en `src/` (no hay paso de build intermedio en los paquetes:
son consumidos como TypeScript fuente, cada app los transpila con su propio
bundler). Esto evita mantener un paso de compilación extra en dos paquetes
que solo existen para compartirse dentro del propio repo.

## packages/shared — el dominio

Un único store de **zustand** (`useErpStore`) contiene todo el estado de la
aplicación: `products`, `variants`, `materials`, `orders`, `movements`
(historial de movimientos de stock). Las acciones del store son la única vía
para mutar datos y son las que aplican las reglas de negocio:

- `addProduct` — crea una figura con una o más variantes.
- `adjustVariantStock` / `adjustMaterialStock` — ajusta stock de una variante
  o de un material (filamento/resina), registra un `StockMovement` y
  **lanza `InsufficientStockError`** si el ajuste dejaría stock negativo.
- `createOrder` — valida que haya stock suficiente para cada línea del
  pedido *antes* de confirmar nada, y si es así crea el pedido, descuenta
  stock de cada variante vendida y registra los movimientos correspondientes
  en una sola actualización atómica del store.

Zustand se eligió porque su API funciona igual en React DOM y en React
Native sin adaptadores, así que **el mismo store se importa tal cual desde
la web y desde la app móvil** — es el corazón de "compartir el mismo
dominio entre plataformas".

### Trade-off: persistencia

El store vive **en memoria** (se reinicia con datos semilla en cada carga
de página / arranque de la app). No hay backend ni base de datos: el
alcance pedido era demostrar el dominio, el design system y los flujos end
to end, no operar un backend real. Ver `docs/decisions/001-persistencia.md`
para el detalle y cómo evolucionar esto a un backend real sin tocar la capa
de UI (las páginas/pantallas ya dependen solo de las acciones del store,
nunca de cómo se guardan los datos).

## apps/web

- **Vite + React 18 + TypeScript + react-router**.
- `src/design-system/`: componentes de interfaz (`Button`, `Card`, `Label`,
  `Callout`, `GridPaper`, `Input`, `Select`) que traducen los componentes del
  design system a HTML/CSS usando *solo* las variables definidas en
  `@octo-erp/design-tokens/src/tokens.css`.
- `src/layout/AppShell.tsx`: cabecera de dos paneles (terracota + verde agua)
  inspirada en el componente `Lamina` del design system, con la navegación
  entre módulos.
- `src/pages/`: `CatalogPage`, `InventoryPage`, `OrdersPage` y sus
  formularios (`ProductForm`, `OrderForm`).
- `e2e/`: pruebas Playwright (ver `docs/testing.md`).

## apps/mobile

- **Expo (SDK 51) + React Native + TypeScript**, sin `react-navigation`: la
  navegación entre los tres módulos es un simple switch de pantalla en
  `App.tsx` (`AppShell` con una barra de pestañas propia), porque con solo
  tres pantallas de nivel superior una librería de navegación completa no
  aporta valor y añade superficie nativa (linking, gestos, stacks) que no se
  usa. Si el producto crece (pantallas de detalle, deep links) es el primer
  punto de extensión — ver `docs/status.md`.
- `src/theme/ThemeContext.tsx`: lee `@octo-erp/design-tokens/src/theme.ts` y
  expone los tokens ya resueltos (claro/oscuro según `useColorScheme`) al
  resto de la app.
- `src/design-system/`: los mismos componentes que en la web (`Button`,
  `Card`, `Label`, `Callout`, `Input`, `Select`) pero con primitivas de React
  Native (`View`, `Text`, `Pressable`, `Modal`) en vez de HTML. `Select` es
  un selector propio con `Modal` + `FlatList` (se evitó añadir
  `@react-native-picker/picker` solo para esto).
- `metro.config.js`: configuración estándar de Expo para monorepos
  (`watchFolders` + `nodeModulesPaths` apuntando a la raíz), necesaria para
  que Metro resuelva `@octo-erp/shared` y `@octo-erp/design-tokens` como
  paquetes de workspace.
- Verificado con `tsc --noEmit` y con `expo export -p web` (bundling real vía
  Metro con `react-native-web`, usado solo como humo de compilación local;
  la plataforma de destino sigue siendo iOS/Android vía Expo Go/EAS).

## Por qué dos implementaciones de componentes y no una sola

Se evaluó usar `react-native-web` para tener un único árbol de componentes
que sirva ambas plataformas. Se descartó porque el pedido explícitamente
separa "dos frontends... adaptados a cada plataforma", y porque React DOM y
React Native tienen primitivas y modelos de layout distintos (flexbox por
defecto en RN, unidades sin `px`, sin CSS real) — forzar una sola base de
componentes términa generando abstracciones con fugas. En su lugar se
comparte lo que sí es correcto compartir: **tokens** (una sola fuente de
verdad de valores) y **dominio** (tipos + store + reglas de negocio), y se
adapta la capa puramente visual a cada plataforma siguiendo la misma
especificación de componentes del design system.
