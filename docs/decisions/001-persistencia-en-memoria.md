# 001 — Persistencia en memoria (sin backend)

**Estado:** aceptado.

## Contexto

El alcance pedido es un ERP funcional (inventario, catálogo, ventas) con dos
frontends que comparten dominio y design system, verificado con pruebas e2e.
No se especificó backend, base de datos ni autenticación.

## Decisión

Todo el estado (`products`, `variants`, `materials`, `orders`, `movements`)
vive en un store de zustand en memoria (`packages/shared/src/store.ts`),
inicializado con datos semilla (`seed.ts`) en cada carga de la app. No hay
persistencia entre recargas ni sincronización entre web y mobile: cada
proceso de cada app tiene su propia copia del store.

## Por qué

- Construir un backend (API + base de datos + auth) es un proyecto en sí
  mismo; hacerlo "rápido y mal" dentro de este alcance habría restado tiempo
  a lo que sí se pidió explícitamente: dominio compartido, design system
  aplicado a dos plataformas, y verificación e2e con capturas.
- Las reglas de negocio (validación de stock, descuento al confirmar un
  pedido, umbrales de reposición) están igualmente demostradas y probadas
  sin necesidad de una base de datos real: viven en las acciones del store,
  no en la UI.

## Trade-offs aceptados

- Los datos no persisten entre sesiones ni se comparten entre la web y la
  app móvil (cada una parte de la misma semilla, pero de forma
  independiente).
- No hay control de concurrencia (dos pestañas del navegador no se
  sincronizan entre sí).
- No hay autenticación ni multiusuario.

## Camino de evolución

El store expone una API de acciones (`addProduct`, `adjustVariantStock`,
`createOrder`, …) que ya es el único punto de mutación de datos usado por
toda la UI. Para pasar a un backend real:

1. Sustituir el cuerpo de cada acción por una llamada a una API (REST o
   similar) que devuelva el nuevo estado, o adoptar una librería de
   sincronización de datos de servidor (TanStack Query, etc.) por encima
   del mismo store.
2. Ninguna pantalla necesita cambios: todas leen del store con selectores
   (`useErpStore(s => s.products)`) y llaman a las acciones, nunca acceden
   a `seed.ts` directamente.
3. La validación de stock (`InsufficientStockError`) se puede mantener en
   el cliente como validación optimista y repetir en el servidor como
   fuente de verdad.
