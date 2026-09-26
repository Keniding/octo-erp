# 004 — Agente de IA + MCP + Cosmos DB para Octo ERP (planificado, no implementado)

**Estado:** especificación escrita, pendiente de decisiones bloqueantes y del proyecto de
ejemplo del usuario. No hay código de este flujo en este repo todavía.

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

## La decisión bloqueante que hay que tomar antes de escribir código

La especificación (sección 10.1) deja explícito que no puede avanzar sin definir si Cosmos
DB reemplaza al store en memoria (`packages/shared/src/store.ts`, ver
[decisión 001](001-persistencia-en-memoria.md)) como la **única** fuente de verdad que
también usan `apps/web`/`apps/mobile` (Opción A), o si es una réplica separada alimentada
por algún mecanismo de sync todavía sin diseñar, solo para que el agente tenga datos
(Opción B). La especificación asume la Opción A por ser la que realmente conecta el agente
con lo que el usuario humano ve en el ERP, pero es una asunción a confirmar, no una decisión
tomada.

## Trade-off de documentar esto en dos repos

- Ventaja: la especificación vive donde está el conocimiento de los patrones que reutiliza
  (Bicep, MCP, Entra ID ya resueltos en producción por Oráculo), sin duplicar ese contexto.
- Costo: alguien que abra solo `octo-erp` sin `oraculo` clonado no ve la especificación
  completa, solo este puntero. Aceptado porque ambos repos son del mismo dueño y se
  desarrollan en la misma sesión de trabajo; si esto deja de ser cierto (el agente pasa a
  ser mantenido por otro equipo, por ejemplo), la especificación completa debería moverse o
  copiarse a `octo-erp/docs/`.
