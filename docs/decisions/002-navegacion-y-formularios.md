# 002 — Navegación simple en mobile, sin react-navigation

**Estado:** aceptado.

## Contexto

La app móvil necesita moverse entre tres módulos: Catálogo, Inventario y
Pedidos. `react-navigation` es el estándar de facto en el ecosistema Expo
para esto.

## Decisión

Se implementó la navegación entre módulos como un `useState<Screen>` en
`App.tsx` con una barra de pestañas propia (`AppShell`), en vez de instalar
`@react-navigation/native` + `@react-navigation/bottom-tabs` +
`react-native-screens` + `react-native-gesture-handler`.

## Por qué

Con solo tres pantallas de nivel superior y sin necesidad de pilas de
navegación, parámetros de ruta, deep links o transiciones nativas,
`react-navigation` añade dependencias nativas (autolinking, gestos) que no
se ejercitan y que complican la verificación en este entorno sin
simulador/dispositivo. Un switch de estado con una barra de pestañas al
estilo del design system cubre el requisito funcional con menos superficie.

## Trade-offs aceptados

- No hay historial de navegación nativo (botón atrás del sistema no
  "vuelve" entre módulos; tampoco hace falta, son hermanos, no una pila).
- No hay deep linking a una pantalla específica.
- Si el producto crece (pantalla de detalle de producto, detalle de
  pedido con su propia ruta), este es el punto donde conviene introducir
  `react-navigation` o `expo-router`.

---

# 003 — Formularios: multi-variante en web, variante única en mobile al alta

**Estado:** aceptado.

## Contexto

`ProductForm` en la web permite agregar varias variantes al crear una figura
(varias filas dinámicas). En mobile, `ProductForm` crea una figura con
**una sola variante** por alta.

## Por qué

Es una simplificación deliberada para mantener el formulario usable en una
pantalla angosta sin un patrón de "filas dinámicas" que en mobile
requeriría más superficie de scroll y gestión de foco. El dominio
(`addProduct` en `packages/shared`) siempre aceptó una lista de variantes —
no hay ninguna limitación del store — así que ampliar el formulario móvil a
múltiples variantes es un cambio acotado a `apps/mobile/src/screens/ProductForm.tsx`
cuando se priorice.
