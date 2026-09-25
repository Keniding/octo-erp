# 003 — Grilla responsive de los formularios multi-fila y botones que no se estiran

**Estado:** aceptado.

## Contexto

El usuario reportó, con una captura del formulario "Nueva figura" en
desktop ancho, dos problemas visuales:

1. El botón `+ Agregar variante` aparecía como una caja enorme que ocupaba
   todo el ancho del fieldset (en vez de medir su propio contenido).
2. La fila de campos de cada variante (`Nombre`, `SKU`, `Precio`,
   `Material`, `Peso`, `Stock`) saltaba de una sola columna en mobile a
   seis columnas fijas a partir de 768px — en tablet (768–1023px) esas seis
   columnas quedaban demasiado angostas para el contenido.

Ambos problemas también afectan a `apps/web/src/pages/OrderForm.tsx`, que
reutiliza las mismas clases (`variant-fieldset`, `variant-row`,
`.ds-button`).

## Decisión

1. `apps/web/src/design-system/button.css`: `.ds-button` ahora fija
   `align-self: flex-start` (y `flex-shrink: 0`). Un botón nunca se estira
   dentro de un contenedor flex en columna con `align-items: stretch` por
   defecto (como `.variant-fieldset`), sin depender de que cada lugar que
   lo usa se acuerde de envolverlo en un `<div>`.
2. `apps/web/src/styles/app.css`: `.variant-row` pasa de
   `1fr` → `repeat(6, 1fr)` en un solo salto a tres pasos:
   - `<480px`: 1 columna.
   - `480–767px`: 2 columnas fijas.
   - `≥768px`: `repeat(auto-fit, minmax(150px, 1fr))` — el número de
     columnas se resuelve solo según el espacio disponible (en vez de un
     `repeat(6, 1fr)` fijo que fuerza seis columnas apretadas justo a
     partir de 768px). En tablet caen ~3-4 columnas por fila; en desktop,
     hasta 6 con ancho real en vez de estirarse innecesariamente.

## Por qué esta solución y no otra

- Fijar `align-self: flex-start` en el componente base (`Button`) es más
  robusto que envolver cada botón suelto en un `<div>` caso por caso: el
  siguiente formulario que se agregue no puede volver a introducir el
  mismo bug por olvido.
- `auto-fit`/`minmax` en vez de más *breakpoints* manuales con conteos de
  columna fijos: se adapta a cualquier ancho intermedio sin necesidad de
  ir agregando un `@media` por cada resolución que se pruebe, y es
  coherente con la regla del design system de no introducir tamaños
  ad-hoc — el `minmax(150px, …)` es el único número nuevo, elegido para
  que ningún campo (`STOCK INICIAL`, `PRECIO (USD)`) se comprima por debajo
  de su ancho legible.

## Verificación

`apps/web/e2e/responsive.spec.ts` se extendió con capturas del formulario
abierto (`catalogo-formulario-*` y `pedidos-formulario-*`) en los 3
breakpoints estándar del proyecto (390/768/1440px), además de las capturas
de página que ya existían. Corridas en `docs/screenshots/`; las 20 pruebas
de `apps/web/e2e/` pasan en verde.
