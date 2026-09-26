# 4. Microsoft Foundry

## Qué es

**Microsoft Foundry** (antes Azure AI Studio / Azure AI Foundry) es la plataforma PaaS
unificada de Azure para IA empresarial: agrupa **modelos** (catálogo de proveedores, no solo
OpenAI), **agentes** (persistentes o efímeros), y **herramientas de plataforma** (búsqueda de
archivos, code interpreter, MCP, SharePoint, y más), todo bajo un mismo **project endpoint**,
con RBAC, tracing y evaluación integrados — la capa que Azure ofrece para no tener que armar
esa infraestructura de agentes desde cero.

## El endpoint del proyecto y sus dos clientes

Toda aplicación Foundry gira alrededor de una URL:

```
https://<recurso>.services.ai.azure.com/api/projects/<proyecto>
```

Y dos clientes que se complementan, no que compiten:

- **Project client** (`AIProjectClient`, del SDK `azure-ai-projects`) — para lo que es
  específico de Foundry y no existe en la API de OpenAI: listar conexiones y deployments de
  modelos, gestionar agentes versionados, datasets, evaluaciones, tracing.
- **Cliente compatible con OpenAI** (`project.get_openai_client()`) — para todo lo que sigue
  el patrón de la industria (Responses API, conversations) contra el catálogo completo de
  modelos de Foundry, no solo los de OpenAI, y con acceso a las tools de plataforma
  (incluido **MCP** como tool nativa — ver más abajo).

La mayoría de las aplicaciones reales usan los dos: el project client para configurar/crear
el agente, el cliente OpenAI-compatible para ejecutarlo.

## Tres formas de tener un agente en Foundry

Son **aditivas**, no alternativas — la misma lógica de agente puede pasar de una a otra sin
reescribirse:

1. **Prompt agent**: un recurso persistente y versionado dentro del proyecto de Foundry
   (`PromptAgentDefinition`), gestionado por Foundry — vive como un activo del proyecto,
   con nombre y versión, independiente del código de la aplicación que lo llama.
2. **Ephemeral agent**: la definición del agente vive en el código de la aplicación (vía
   Microsoft Agent Framework, sección 5); cada ejecución construye el agente en el momento
   y llama a la Responses API. Se versiona junto con el resto del código, no como un activo
   separado del proyecto.
3. **Hosted agent** (en preview): el mismo código de Agent Framework se empaqueta como
   contenedor, y Foundry lo aloja, escala, y expone como su propio endpoint — para que
   *otros* sistemas lo consuman como servicio.

## MCPTool: cómo Foundry se conecta a un servidor MCP externo

Esta es la pieza específica que quedó bloqueada en la especificación original de este
proyecto (`docs/decisions/004`): Foundry expone **MCP como una tool de plataforma**
(`MCPTool`) — se le puede decir a un agente de Foundry "tenés disponible este servidor MCP
en esta URL", y Foundry mismo actúa como **cliente MCP** contra ese servidor cuando el
modelo decide usar una de sus tools. El punto que faltaba resolver era el mecanismo exacto
de autenticación **entrante** — cómo protege el servidor MCP custom (`mcp_server.py` de
este proyecto) las llamadas que le llegan *desde* Foundry, vía Entra ID/Easy Auth, sin
exponerlo anónimo a cualquiera en internet.

Este proyecto resolvió el problema de fondo (que el agente pueda usar las tools reales) por
otro camino — ver sección 7 — sin necesitar esa pieza de auth entrante todavía, porque el
agente **no es** un agente de Foundry hospedado: es un agente escrito a mano que hace de
**cliente MCP saliente**. La pieza de MCPTool/auth entrante queda pendiente para el día que
se decida usar Foundry como host real del agente (prompt o hosted agent), no como hoy (solo
como proveedor del modelo, vía el cliente compatible con OpenAI).

## Autenticación

Entra ID es el mecanismo recomendado en todos los endpoints de Foundry
(`DefaultAzureCredential` / `ManagedIdentityCredential` en producción) — las API keys
siguen existiendo pero solo en el endpoint `/openai/v1`, y quedan documentadas como la
opción menos preferida. Este proyecto sigue esa recomendación al pie de la letra: el
recurso de IA (`octo-erp-ai`, ver decisión 010) tiene auth 100% Entra ID, sin ninguna key
guardada en ningún lado — Managed Identity de la Function App en producción, la sesión de
`az login` del desarrollador en local.
