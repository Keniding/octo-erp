# 6. Python como núcleo

## Por qué el ecosistema entero converge en Python

No es casualidad ni preferencia — es dónde vive el ecosistema real de piezas que este stack
necesita:

- **El SDK oficial de MCP** (`mcp` en PyPI) es Python de punta a punta — cliente, servidor,
  transportes, todo. Es el paquete que este proyecto usa directamente
  (`mcp.server.mcpserver.MCPServer`, `mcp.ClientSession`, `mcp.client._memory`).
- **El SDK de Azure OpenAI/Foundry** (`openai`, `azure-ai-projects`) tiene su superficie más
  completa y más al día en Python — C#/.NET existe y está soportado, pero la documentación
  y los ejemplos oficiales de Microsoft Foundry arrancan casi siempre en Python.
- **Microsoft Agent Framework** tiene Python como una de sus dos superficies principales
  (junto con C#) — con nombres de API que, salvo casos puntuales, calcan el diseño de la
  versión .NET.
- **`azure-identity`** (Entra ID / Managed Identity / `DefaultAzureCredential`) es el mismo
  patrón de auth que ya usa este proyecto contra Cosmos DB (`repositories/cosmos.py`) y
  contra el recurso de IA (`agent_chat.py`) — una sola forma de autenticarse contra *todo*
  Azure, sin importar el servicio.
- El **modelo de concurrencia async/await** de Python encaja naturalmente con la naturaleza
  de un agente: cada paso del loop (llamar al modelo, ejecutar una tool, leer de una base de
  datos) es una espera de I/O, no cómputo — exactamente el caso de uso para el que
  `asyncio` fue diseñado.

## El principio de diseño que se sostiene sin importar el framework

Más allá de qué SDK o framework se use arriba, hay un principio de arquitectura que este
proyecto sostiene de punta a punta, y que vale para *cualquier* stack de agentes en
cualquier lenguaje:

> **El dominio de negocio no sabe que existe un agente.**

`domain/service.py` (las reglas de negocio: validar stock, crear pedidos, ajustar
inventario) no importa nada de `mcp`, `openai`, ni conoce la existencia de un LLM. Lo llaman
tres capas distintas — la API REST (`rest_api.py`), el servidor MCP (`mcp_server.py`), y el
agente (`agent_chat.py`, indirectamente, vía MCP) — pero la regla "nunca vender más stock
del disponible" vive en **un solo lugar**, escrita una sola vez, sin ninguna dependencia de
IA. Si mañana se agrega Microsoft Agent Framework, o se cambia de proveedor de modelo, o se
conecta Foundry como host real — esa capa no se toca. Es la misma separación que en
cualquier arquitectura de puertos y adaptadores (*hexagonal*): el dominio en el centro, los
adaptadores (REST, MCP, agente) alrededor, cada uno hablando el protocolo que le
corresponde pero llamando al mismo núcleo.

Esto es, en el fondo, la respuesta a "por qué Python en el centro de todo esto" no es solo
"porque los SDKs están ahí" — es que el lenguaje de la plataforma de agentes es un detalle
de infraestructura, y un buen diseño hace que ese detalle sea reemplazable sin tocar las
reglas de negocio reales.
