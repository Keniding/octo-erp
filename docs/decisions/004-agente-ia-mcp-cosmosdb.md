# 004 — Agente de IA + MCP + Cosmos DB para Octo ERP

**Estado:** especificación escrita, decisión bloqueante resuelta (ver
[decisión 005](005-cache-frontend-vs-fuente-de-verdad.md): Cosmos DB es la única fuente de
verdad). Dominio de negocio y servidor MCP custom **implementados y probados** en
`services/octo-erp-agent/` (20/20 tests reales pasando, incluyendo un round-trip end-to-end
sobre el protocolo MCP real — ver su `README.md`). Pendiente: conexión a una cuenta Cosmos
DB real (sin credenciales de Azure disponibles en el entorno de desarrollo de esta sesión),
infraestructura Bicep, y el proyecto de ejemplo del usuario para afinar el mecanismo exacto
de auth entre Foundry y el MCP custom.

## Contexto

Se planea agregar una capa de agente conversacional (Python, Azure AI Foundry) sobre los
datos de Octo ERP, usando MCP (Model Context Protocol) para conectar el agente tanto a un
servidor nativo de Microsoft para Cosmos DB como a un servidor MCP custom con las reglas de
negocio del ERP (validación de stock, creación de pedidos). Todo desplegado serverless en
Azure (Function Apps Consumption + Cosmos DB Serverless), con autenticación Entra ID,
siguiendo como referencia los patrones ya probados en producción del proyecto hermano
**Oráculo** (`github.com/Keniding/oraculo`) — que ya expone un servidor MCP sobre Azure
Functions y protege un endpoint con Entra ID/Easy Auth.

## Dónde está la especificación completa

La especificación técnica completa (arquitectura, esquema de Cosmos DB, las 6 tools MCP
propuestas mapeadas desde `packages/shared/src/store.ts`, el mecanismo de auth salto por
salto, costos, y el checklist de decisiones pendientes) vive en el repo `oraculo`:

**`oraculo/docs/10-especificacion-2-agente-octo-erp.md`**

Se escribió allá (no acá) porque ese repo ya tiene la convención de documentación numerada y
los patrones de infraestructura (Bicep, MCP sobre Azure Functions, Easy Auth) que esta
especificación reutiliza explícitamente en vez de reinventar.

## La decisión bloqueante — resuelta

Confirmado: **Opción A**. Cosmos DB reemplaza al store en memoria
(`packages/shared/src/store.ts`, ver [decisión 001](001-persistencia-en-memoria.md)) como la
única fuente de verdad de datos de negocio. El detalle de cómo convive esto con caché del
lado del frontend (preferencias de UI, lazy loading) está en
[decisión 005](005-cache-frontend-vs-fuente-de-verdad.md).

## Dónde está el código (implementado, no solo especificado)

`services/octo-erp-agent/` — paquete Python (`uv`) con:

- `src/octo_erp_agent/domain/` — reglas de negocio, puerto 1:1 de
  `packages/shared/src/store.ts` (mismos IDs de datos semilla, mismas validaciones).
- `src/octo_erp_agent/repositories/` — `InMemoryRepository` (tests, sin Azure) y
  `CosmosRepository` (real contra Azure Cosmos DB, sin verificar aún contra una cuenta real).
- `src/octo_erp_agent/mcp_server.py` — servidor MCP custom, mismo patrón que
  `oraculo/mcp_server.py`.
- `tests/` — 20 tests, corren con `uv run pytest` (ver `README.md` del paquete para el
  detalle de qué está probado de verdad y qué no).

## Trade-off de documentar esto en dos repos

- Ventaja: la especificación vive donde está el conocimiento de los patrones que reutiliza
  (Bicep, MCP, Entra ID ya resueltos en producción por Oráculo), sin duplicar ese contexto.
- Costo: alguien que abra solo `octo-erp` sin `oraculo` clonado no ve la especificación
  completa, solo este puntero. Aceptado porque ambos repos son del mismo dueño y se
  desarrollan en la misma sesión de trabajo; si esto deja de ser cierto (el agente pasa a
  ser mantenido por otro equipo, por ejemplo), la especificación completa debería moverse o
  copiarse a `octo-erp/docs/`.
