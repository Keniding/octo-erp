# 5. Microsoft Agent Framework (MAF)

## Qué es y de dónde viene

**Microsoft Agent Framework** es el framework de Microsoft para construir aplicaciones de
IA agéntica — el **sucesor directo de Semantic Kernel y AutoGen**, hecho por los mismos
equipos. La idea de fondo: tomar las abstracciones simples de agente de AutoGen y las
características empresariales de Semantic Kernel (estado por sesión, seguridad de tipos,
middleware, telemetría), y sumarles **workflows basados en grafos** para orquestación
explícita de varios agentes (sección 3) — unificando en un solo framework lo que antes eran
dos herramientas con filosofías distintas.

> Está en preview/RC (`1.0.0rc*` en Python al momento de escribir esto) — los nombres de API
> pueden cambiar entre versiones; tratar esta sección como mapa conceptual, no como
> contrato de API congelado.

## Las dos primitivas centrales

MAF ofrece exactamente dos abstracciones de alto nivel — la primera decisión de diseño es
elegir cuál corresponde (ver la tabla completa en la sección 3):

- **`AIAgent`** (C#) / **`Agent`** (Python): el "contenedor" de un agente único con tools —
  procesa entrada, decide, llama herramientas, genera respuesta. Es la unidad fundamental,
  equivalente conceptual a lo que este proyecto escribió a mano en `agent_chat.py`.
- **`Workflow`**: un grafo de `Executor`s conectados por `edge`s, para orquestación
  multi-agente explícita (sección 3) — un `AIAgent` pasado a un `Workflow` se envuelve
  automáticamente como ejecutor, sin adaptación manual.

## Las piezas alrededor del agente

- **Model clients**: la conexión al proveedor del modelo (chat completions o Responses
  API) — Azure OpenAI, Foundry (`FoundryChatClient`), Anthropic, OpenAI directo, Ollama,
  Copilot. Es la pieza que, en este proyecto, se reemplazó por una llamada directa al SDK
  de `openai` contra Azure OpenAI — sin pasar por la capa de abstracción de MAF.
- **Sesión / thread** (`AgentSession`): los agentes de MAF son **stateless por defecto** —
  la conversación multi-turno vive en la sesión, no en el agente. Sin sesión, cada
  ejecución empieza de cero. (Este proyecto tampoco tiene sesión — cada mensaje al chat es
  independiente, ver decisión 010, "Trade-offs aceptados" — la misma limitación, resuelta
  distinto: acá no hay sesión en absoluto, en MAF sería una pieza explícita a agregar.)
- **Context providers**: memoria e inyección de contexto persistente entre turnos/sesiones.
- **Middleware**: intercepta acciones del agente — logging, *guardrails*, aprobación humana
  antes de ejecutar una tool sensible (`ApprovalRequiredAIFunction`).
- **Clientes MCP**: MAF tiene soporte nativo para conectarse a servidores MCP (stdio, HTTP,
  websocket) como fuente de tools — la misma idea que este proyecto implementó a mano con
  el SDK de `mcp` directamente, sin la capa de MAF encima.

## Tools en MAF

Una tool es una función normal, decorada — `[Description]` en C#, `@tool` o
`Annotated[..., Field(...)]` en Python — y el agente la descubre y la llama solo, sin que el
desarrollador tenga que traducirla a mano a un JSON Schema (MAF lo genera automáticamente a
partir de la firma de la función). Es la misma idea conceptual que la conversión manual que
hace `agent_chat.py` de este proyecto (`_mcp_tool_to_openai_schema`) — con la diferencia de
que MAF automatiza ese paso para tools nativas de Python, mientras que este proyecto
convierte tools MCP (ya con su propio JSON Schema) al formato que espera la API de OpenAI,
sin necesitar la generación automática porque el schema ya viene armado del lado del
servidor MCP.

## Por qué este proyecto NO usa MAF (todavía)

Decisión explícita, no una omisión: `agent_chat.py` implementa a mano el equivalente de un
`Agent` de MAF con un cliente MCP — el mismo patrón conceptual, sin la dependencia del SDK.
Las razones:

- **Es un solo agente, sin orquestación multi-agente** — la ventaja diferencial más grande
  de MAF (los `Workflow`s de la sección 3) no aplica todavía a este problema.
- **Menos superficie de dependencias** en un momento donde ya se estaba peleando con
  estabilidad de deploy en Azure Functions (ver `docs/decisions/007`) — agregar un
  framework más (en preview/RC) a esa ecuación era riesgo innecesario para el alcance real
  pedido.
- El **loop de tool-calling manual es lo bastante simple** (menos de 40 líneas, ver
  `_handle_message_llm`) como para no necesitar una abstracción encima todavía — coincide
  con la propia recomendación del framework: no uses una abstracción para algo que una
  función simple ya resuelve bien.

Si el alcance crece hacia **multi-agente real** (por ejemplo, el patrón *handoff* de la
sección 3, con un agente separado por dominio), ahí es donde adoptar MAF empieza a pagar su
propio costo de complejidad — hoy, para un agente único, no.
