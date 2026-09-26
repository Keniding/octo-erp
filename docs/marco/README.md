# Marco teórico — Agentes de IA, MCP, Azure AI Foundry y Microsoft Agent Framework

Esta carpeta es **puramente teórica**: el marco conceptual detrás de lo que se construyó en
`services/octo-erp-agent/` (decisiones 004, 007, 010), separado a propósito de la
documentación de decisiones técnicas (`docs/decisions/`, que explica *qué* se hizo y *por
qué* en este repo puntual). Acá el objetivo es otro: dejar por escrito el marco conceptual
completo — para una charla sobre agentes, orquestación, Python y MCP — con foco en **Python**
como el lenguaje que atraviesa todo el stack (el SDK oficial de MCP, el SDK de Azure OpenAI,
Microsoft Agent Framework, y el propio dominio de negocio de este proyecto).

## Índice

1. [Agentes de IA](01-agentes-de-ia.md) — qué es un agente (vs. una función determinista vs.
   una llamada simple a un LLM), el loop agente, tool-calling, el patrón ReAct.
2. [Model Context Protocol (MCP)](02-model-context-protocol.md) — por qué existe, sus
   primitivas (tools/resources/prompts), roles (host/client/server), el handshake del
   protocolo, y los transportes (stdio, HTTP, streamable HTTP, en memoria).
3. [Orquestación de agentes](03-orquestacion-de-agentes.md) — de un agente con tools a varios
   agentes coordinados: secuencial, concurrente, handoff, group chat, planificador/workers.
4. [Microsoft Foundry](04-microsoft-foundry.md) — la plataforma unificada de Azure para
   modelos + agentes + tools: el project endpoint, los dos clientes, las tres formas de tener
   un agente (prompt/ephemeral/hosted), MCPTool, auth con Entra ID.
5. [Microsoft Agent Framework (MAF)](05-microsoft-agent-framework.md) — el sucesor de
   Semantic Kernel y AutoGen: `Agent` vs. `Workflow`, las piezas (sesión, context providers,
   middleware, clientes MCP), y por qué este proyecto NO lo adopta todavía.
6. [Python como núcleo](06-python-como-nucleo.md) — por qué el ecosistema entero (MCP,
   Foundry, MAF, y el dominio de este proyecto) converge en Python, y qué principio de
   diseño (separar dominio de orquestación) se sostiene sin importar qué framework se use
   arriba.
7. [Aplicado a Octo ERP](07-aplicado-a-octo-erp.md) — el puente entre la teoría y el código
   real de este repo: qué de todo lo anterior está implementado, qué está simplificado a
   propósito, y qué queda como deuda técnica documentada (no evadida).

## Cómo se conecta con el resto del repo

- `docs/decisions/004-agente-ia-mcp-cosmosdb.md`, `005-...`, `007-...`, `010-...` — las
  decisiones técnicas concretas tomadas en este proyecto, con su *por qué* puntual.
- `services/octo-erp-agent/src/octo_erp_agent/mcp_server.py` — el servidor MCP real.
- `services/octo-erp-agent/src/octo_erp_agent/agent_chat.py` — el agente real (LLM +
  tool-calling vía MCP).
- Esta carpeta (`docs/marco/`) — el marco conceptual detrás de esas dos piezas, sin atarse a
  los detalles de implementación de este repo puntual.
