# Estado del proyecto

Última actualización: 2026-09-25.

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
  errores.
- **Mobile** (`apps/mobile`, Expo): las mismas tres pantallas, mismo dominio
  compartido, componentes de interfaz propios en React Native siguiendo la
  misma especificación visual. `tsc --noEmit` sin errores y bundling
  verificado con `expo export -p web` (Metro resuelve correctamente los
  paquetes de workspace vía `metro.config.js`).
- Pruebas e2e con Playwright en `apps/web` (14 tests, todos en verde):
  3 flujos clave (alta de producto, ajuste de inventario, creación de
  pedido) más sus casos de validación negativa, y 9 capturas de
  responsividad (3 páginas × 3 breakpoints) guardadas en
  `docs/screenshots/`.
- Documentación en `docs/`: arquitectura, uso del design system, decisiones
  con trade-offs, esta página de estado, y cómo correr todo.
- `CLAUDE.md` en la raíz con las reglas persistentes pedidas.

## Falta / próximos pasos sugeridos

- **Backend real**: hoy todo el estado es en memoria (ver
  `docs/decisions/001-persistencia-en-memoria.md`). El store ya está
  diseñado para que esto sea un cambio localizado a `packages/shared/src/store.ts`.
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
