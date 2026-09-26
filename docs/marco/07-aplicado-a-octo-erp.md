# 7. Aplicado a Octo ERP — el puente entre la teoría y el código real

## Mapa: concepto → archivo real

| Concepto (secciones 1-6) | Dónde vive en este repo |
|---|---|
| Servidor MCP (tools) | `services/octo-erp-agent/src/octo_erp_agent/mcp_server.py` — 9 tools reales sobre `domain/service.py` |
| Dominio de negocio (sin IA) | `services/octo-erp-agent/src/octo_erp_agent/domain/service.py` |
| Cliente MCP + host del agente | `services/octo-erp-agent/src/octo_erp_agent/agent_chat.py` |
| Loop de agente (ReAct) | `_handle_message_llm` en `agent_chat.py` — el `for` que llama al modelo, ejecuta tools, repite |
| Model client (Foundry-adjacente) | `AzureOpenAI` del SDK `openai`, auth Entra ID vía `azure-identity` |
| Transporte MCP | `mcp.client._memory.InMemoryTransport` — protocolo real, sin red (sección 2) |
| Auth Entra ID de punta a punta | Managed Identity de la Function App ↔ Cosmos DB **y** ↔ el recurso de IA — mismo patrón, cero keys |

## Qué de la teoría está implementado tal cual

- **Un agente único con tool-calling real** (sección 1) — completo, probado contra Azure
  real (`docs/decisions/010`).
- **MCP real** (sección 2) — protocolo real (`initialize`/`list_tools`/`call_tool` con el
  SDK oficial), transporte simplificado (en memoria en vez de HTTP).
- **Auth Entra ID en todos los saltos** (sección 4) — sin ninguna key en ningún lado, ni
  para Cosmos DB ni para el modelo.

## Qué está simplificado a propósito (y por qué)

- **Transporte MCP en memoria, no HTTP externo.** El servidor MCP y el agente que lo
  consume corren en el **mismo proceso** (`octo-erp-inc`, una sola Function App) — a
  diferencia de `oraculo`, que despliega su servidor MCP (`oraculo-mcp`) y su backend web
  (`oraculo-web`) como **dos Function Apps separadas**. La arquitectura "correcta" (MCP
  como servicio externo, consumido por HTTP real) queda documentada como pendiente — no
  evadida, decidida explícitamente así por el costo/riesgo de crear un recurso de Azure
  Functions más en una sesión que ya gastó horas peleando con fallas intermitentes de
  deploy (`docs/decisions/007`). Ver la entrada correspondiente en `docs/status.md`.
- **Sin Foundry como host del agente.** El agente no es un *prompt agent* ni un *hosted
  agent* de Foundry (sección 4) — es un agente escrito a mano que usa el recurso de IA
  **solo como proveedor del modelo** (vía el SDK de `openai` contra un endpoint de Azure
  OpenAI/Cognitive Services). No hay `AIProjectClient`, no hay `MCPTool` de Foundry, no hay
  auth entrante de Foundry hacia el servidor MCP — porque no hace falta: el agente es el
  cliente MCP, no Foundry.
- **Sin Microsoft Agent Framework.** El loop de tool-calling está escrito a mano (sección
  5) — deliberado, no por desconocimiento del framework: para un agente único, sin
  orquestación multi-agente, la abstracción de MAF no paga su propio costo todavía.
- **Sin sesión/memoria entre mensajes.** Cada llamada a `/api/agent/chat` es independiente
  — no hay `AgentSession` ni equivalente. El frontend tampoco manda historial hoy.

## El camino de evolución, si el alcance crece

Esta tabla es, a propósito, la guía para decidir *cuándo* cada pieza de la teoría empieza a
pagar su costo de adopción — no antes:

| Si aparece esta necesidad… | La pieza teórica que resuelve |
|---|---|
| Varios dominios de negocio distintos, cada uno con su propio agente especializado | Orquestación *handoff* o *group chat* (sección 3), vía MAF `Workflow` |
| El agente necesita recordar la conversación entre mensajes | `AgentSession`/context provider de MAF, o una sesión propia con estado |
| Otro sistema (no solo esta web) necesita consumir el mismo agente | Publicar el agente como *hosted agent* de Foundry (sección 4) |
| El servidor MCP necesita ser consumido por sistemas fuera de esta Function App | Separar `mcp_server.py` en su propio despliegue (como `oraculo`), transporte HTTP real |
| Acciones más sensibles (montos grandes, cancelaciones) | Middleware de aprobación humana (`ApprovalRequiredAIFunction` en MAF, o un equivalente propio) |

Ninguna de estas es una falla del diseño actual — son, literalmente, la lista de qué
hipótesis de "no lo necesitamos todavía" habría que revisar primero.
