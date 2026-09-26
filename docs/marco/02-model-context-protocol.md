# 2. Model Context Protocol (MCP)

## El problema que resuelve

Antes de MCP, conectar un agente a una herramienta externa (una base de datos, una API, un
sistema de archivos) era **integración a medida**: cada combinación agente↔herramienta
necesitaba su propio código de conexión, escrito una vez por cada par. Con *N* agentes y *M*
herramientas, eso son *N×M* integraciones distintas — el mismo problema que resolvió USB para
periféricos, o HTTP para clientes/servidores web: un **protocolo estándar** en el medio
convierte *N×M* integraciones en *N + M*.

**Model Context Protocol** (MCP, publicado por Anthropic como estándar abierto) es
exactamente eso: un protocolo — no un producto, no un SDK de una sola empresa — para que
*cualquier* aplicación de IA (el "host") se conecte a *cualquier* servidor de herramientas,
sin que ninguno de los dos lados conozca de antemano al otro. Es la razón por la que este
proyecto puede exponer las mismas tools (`mcp_server.py`) a un agente propio escrito a mano
(`agent_chat.py`) **y** a Azure AI Foundry **y** a cualquier otro cliente MCP futuro — sin
tocar el servidor.

## Las tres primitivas

MCP define tres tipos de capacidad que un servidor puede exponer:

| Primitiva | Qué es | Quién la invoca | Ejemplo en este proyecto |
|---|---|---|---|
| **Tools** | Funciones con efectos — el servidor las ejecuta cuando el cliente lo pide | El modelo (indirectamente, vía tool-calling) | `create_order`, `adjust_variant_stock` |
| **Resources** | Datos que el servidor expone para lectura (archivos, filas, documentos) | La aplicación host, para dar contexto | (no usado en este proyecto todavía) |
| **Prompts** | Plantillas de prompt reutilizables que el servidor sugiere | El usuario/host, explícitamente | (no usado en este proyecto todavía) |

Este proyecto usa **solo Tools** — es, con diferencia, la primitiva más usada en la práctica,
porque es la que le da a un agente la capacidad de *actuar*, no solo de *leer contexto*.

## Roles: Host, Client, Server

- **Servidor MCP**: expone tools/resources/prompts. No sabe nada de LLMs — es una capa de
  negocio pura. En este proyecto: `mcp_server.py`, que a su vez llama a `domain/service.py`
  (las reglas de negocio reales, sin ninguna dependencia de IA).
- **Cliente MCP**: habla el protocolo del lado de quien *consume* tools — hace el handshake,
  pide la lista de tools, ejecuta llamadas. No decide *qué* tool llamar, solo la ejecuta
  cuando alguien (normalmente un LLM) se lo pide.
- **Host**: la aplicación que integra uno o más clientes MCP y un LLM, y conecta las
  decisiones del modelo con las ejecuciones del cliente. En este proyecto,
  `agent_chat.py` es el host: tiene el LLM (Azure OpenAI) de un lado y un cliente MCP del
  otro, y hace de puente.

## El protocolo, en la práctica

MCP corre sobre JSON-RPC 2.0. La secuencia real (la misma que ejecuta
`tests/test_mcp_server.py` de este proyecto, cliente oficial contra servidor real, sin
mocks):

```
1. initialize        → el cliente y el servidor negocian versión de protocolo y capacidades.
2. tools/list         → el cliente pide el catálogo de tools disponibles (nombre,
                         descripción, JSON Schema de parámetros) — esto es lo que se
                         traduce 1 a 1 al formato "tools" que espera la API de un LLM.
3. tools/call          → el cliente pide ejecutar una tool puntual con argumentos concretos;
                         el servidor la corre y devuelve el resultado (texto/JSON) o un
                         error.
```

No hay SQL crudo ni acceso directo a la base de datos expuesto al modelo en ningún momento —
el modelo solo ve nombres de tools y sus descripciones; la ejecución real siempre pasa por
código escrito por un humano (`domain/service.py`), que es quien de verdad decide qué está
permitido.

## Transportes: el protocolo es el mismo, el "cable" cambia

MCP separa el protocolo (los mensajes JSON-RPC) del transporte (cómo viajan esos mensajes)
— la misma razón por la que HTTP funciona igual sobre Ethernet o WiFi:

- **stdio**: el servidor corre como subproceso local, cliente y servidor se hablan por
  stdin/stdout. Típico para tools que corren en la misma máquina que el host (ej. un
  servidor de archivos local).
- **HTTP + SSE** (formato original, ahora legado): el servidor es un proceso HTTP aparte;
  las respuestas del servidor al cliente viajaban por Server-Sent Events.
- **Streamable HTTP** (el estándar actual): HTTP normal, con la opción de mantener un stream
  abierto cuando hace falta — es lo que expone este proyecto en `/mcp`, y lo que usaría
  Azure AI Foundry (u otro cliente externo real) para conectarse por red.
- **En memoria**: sin red en absoluto — cliente y servidor corren en el mismo proceso,
  comunicados por streams de Python (`asyncio`) en vez de un socket. Es una simplificación
  legítima para testing, o para cuando cliente y servidor conviven en el mismo despliegue
  (como hace hoy `agent_chat.py` de este proyecto, ver sección 7) — el protocolo hablado es
  exactamente el mismo, solo cambia el transporte.

Este punto es clave para no confundir "usa MCP" con "hace una llamada de red": lo que hace
que algo sea MCP es que habla el protocolo (`initialize`/`list_tools`/`call_tool` con el SDK
oficial), no el medio físico por el que viaja.
