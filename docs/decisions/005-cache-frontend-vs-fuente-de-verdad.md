# 005 — Dos clases de memoria: Cosmos DB como fuente de verdad, caché de frontend aparte

**Estado:** aceptado (confirma y cierra la pregunta bloqueante que dejó abierta la
[decisión 004](004-agente-ia-mcp-cosmosdb.md), sección "la pregunta que hay que responder
primero" — ver `oraculo/docs/10-especificacion-2-agente-octo-erp.md`, sección 10.1).

## Contexto

Al planificar el agente de IA + MCP + Cosmos DB (decisión 004), quedó una pregunta
bloqueante sin resolver: si Cosmos DB iba a ser la única fuente de verdad de los datos del
ERP (reemplazando el store en memoria de `packages/shared/src/store.ts`) o una réplica
separada solo para que el agente tuviera algo que consultar.

## Decisión

**Cosmos DB es la única fuente de verdad de los datos de negocio** (productos, variantes,
materiales, pedidos, movimientos de stock). Punto. No hay una segunda copia de estos datos
en ningún otro lado que se considere autoritativa.

Separado de eso, y sin contradecirlo, hay una **segunda clase de memoria** que sí vive del
lado del frontend — la distinción estándar en cualquier desarrollo con datos de servidor:

| Clase | Qué guarda | Dónde vive | Fuente de verdad |
|---|---|---|---|
| **Datos de negocio** | Catálogo, inventario, pedidos, movimientos de stock | Cosmos DB | Cosmos DB — siempre. El frontend nunca decide un valor de stock/precio/pedido por su cuenta, solo lo refleja. |
| **Caché de frontend** | (a) Preferencias de UI (tema, filtros activos, última pestaña vista) — persistentes entre sesiones pero sin valor de negocio. (b) Caché de lectura para *lazy loading* (resultados de queries ya traídas, para no re-pedir de la red en cada render/navegación) — con invalidación, nunca la respuesta "correcta" si hay duda. | `localStorage`/`AsyncStorage` para (a); una librería de cache de datos de servidor (TanStack Query / React Query en `apps/web`, `@tanstack/react-query` también sirve en `apps/mobile` con Expo) para (b) | Ninguna — es una copia temporal y descartable de lo que ya dijo Cosmos DB vía la API. Si el caché y el servidor difieren, gana el servidor. |

## Qué cambia en el código, concretamente

Hoy `packages/shared/src/store.ts` (zustand) mezcla las dos cosas: es a la vez "estado de
UI" y "fuente de verdad de negocio", porque no había backend (ver
[decisión 001](001-persistencia-en-memoria.md)). Cuando exista la API respaldada por
Cosmos DB (`services/octo-erp-agent`, ver su README), el store deja de ser la fuente de
verdad:

- Las acciones de negocio (`addProduct`, `adjustVariantStock`, `createOrder`, ...) pasan a
  ser llamadas HTTP a esa API, no mutaciones de un objeto en memoria.
- `apps/web`/`apps/mobile` adoptan TanStack Query para leer/cachear esos datos (con
  invalidación tras cada mutación — patrón estándar `useQuery`/`useMutation`), en vez de
  que zustand guarde la lista de productos.
- zustand (o el hook de estado que se use) queda **solo** para estado de UI puro que nunca
  necesita persistir en el servidor: qué formulario está abierto, filtros seleccionados,
  tema claro/oscuro.

Esto no es una tarea de esta sesión (no se tocó `apps/web`/`apps/mobile` todavía) — queda
registrado acá para que quien retome esto no reintroduzca la ambigüedad "¿esto vive en el
store o en el servidor?" que esta decisión ya resuelve: **si es dato de negocio, vive en
Cosmos DB y se cachea; si es preferencia de UI, vive en el cliente y no se sincroniza**.
