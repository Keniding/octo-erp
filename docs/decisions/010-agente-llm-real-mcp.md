# 010 — Agente con LLM real, tool-calling vía MCP real (no un intérprete de comandos)

**Estado:** implementado y probado contra Azure real (Entra ID, sin keys). El intérprete
por comandos anterior (decisión 008) queda como modo explícito sin LLM
(`AGENT_LLM_DISABLED=1`), no como fallback automático.

## Contexto

La sección "Agente" (decisión 008) arrancó como un intérprete de comandos por regex,
documentado ahí mismo como "el punto exacto donde después se conecta un LLM real" — bloqueado
en ese momento por la falta de un mecanismo de auth Entra ID entre Foundry y un MCP
custom. Se decidió no esperar más a esa pieza específica (auth de Foundry llamando
*hacia* nuestro MCP) y en cambio construir el loop del agente *nosotros*, como cliente MCP,
evitando esa dependencia por completo.

## Decisión

- **Recurso de Azure AI Foundry dedicado a octo-erp** (`octo-erp-ai`, `rg-octo-erp-dev`,
  `eastus2`), separado del que ya usa `oraculo` (`rg-foundry-henry`) — decisión explícita
  del usuario para no compartir cuota/billing entre proyectos. Modelo desplegado:
  `gpt-5.4-nano` (mismo modelo que usa `oraculo` en producción para tool-calling).
- **Auth 100% Entra ID, cero keys**: el endpoint del recurso está hardcodeado en
  `agent_chat.py` (no es secreto — sin un token válido no sirve para nada) y la
  autenticación es `DefaultAzureCredential` + `get_bearer_token_provider` contra
  `https://cognitiveservices.azure.com/.default` — Managed Identity de la Function App en
  producción, tu `az login` en local. Mismo patrón que `repositories/cosmos.py` ya usa
  contra Cosmos DB. Rol otorgado: `Cognitive Services OpenAI User`, scopeado a la cuenta.
- **Tool-calling vía MCP real, no llamadas directas a Python**: `_handle_message_llm` abre
  un `ClientSession` real (`mcp.client._memory.InMemoryTransport`) contra
  `mcp_server.mcp` — el mismo objeto servidor MCP que expone `/mcp` para Foundry o cualquier
  otro cliente externo. Las tools que el modelo ve (`list_tools()`) y ejecuta
  (`call_tool()`) son las 9 tools reales de `mcp_server.py`, incluidas dos nuevas agregadas
  en esta sesión: `adjust_material_stock` y `list_orders` (más `find_variant_by_sku`, que ya
  existía en `domain/service.py` pero no estaba expuesta como tool MCP). Esto evita
  mantener dos implementaciones paralelas del "catálogo de acciones que el agente puede
  hacer" — una sola, la que ya usa/probará cualquier cliente MCP real.
- **Sin fallback silencioso si el LLM falla** (pedido explícito del usuario: *"no deseo
  fallback porque el funcionamiento sería falso"*). Si la llamada al modelo falla estando
  habilitado, el chat devuelve un error honesto ("No pude conectar con el modelo de IA...")
  — nunca cae a una respuesta por regex que podría coincidir por casualidad y aparentar que
  el modelo entendió cuando en realidad la llamada nunca respondió. El modo determinístico
  (`_handle_message_deterministic`, el código de la decisión 008) sigue existiendo pero solo
  se activa con `AGENT_LLM_DISABLED=1` explícito — un modo, no una degradación oculta.

## Por qué

- **Loop del agente propio en vez de Foundry Agent Service hospedado**: evita necesitar el
  mecanismo de auth Entra ID *entrante* (Foundry llamando a nuestro MCP con MCPTool) que
  seguía bloqueado por falta de un proyecto de ejemplo — nuestro backend es el *cliente* MCP
  saliente, no el servidor recibiendo llamadas de Foundry, así que ese bloqueante deja de
  aplicar.
- **MCP en memoria (`InMemoryTransport`) en vez de un HTTP self-call**: evita la complejidad
  y latencia de que la Function App se llame a sí misma por HTTP para ejecutar cada tool,
  sin perder nada de "es MCP real" — mismo protocolo, mismos objetos `Tool`/`ClientSession`
  que usaría un cliente externo real, solo sin la vuelta de red.
- **Recurso de Foundry separado del de oraculo**: pedido explícito del usuario tras
  preguntarle — separa cuota, costo y radio de impacto entre los dos proyectos.
- **Sin fallback**: la razón la dio el usuario directamente — un fallback que coincide por
  casualidad con la intención real del mensaje simula inteligencia que no está ahí en ese
  momento. Mejor un error visible que una respuesta correcta por casualidad.

## Verificado corriendo de verdad

- `tests/test_agent_chat.py` (14 tests, modo `AGENT_LLM_DISABLED=1`): mismo comportamiento
  exacto que la decisión 008, sin tocar Azure.
- `tests/test_agent_chat_llm.py` (4 tests, opt-in con `RUN_LLM_INTEGRATION_TESTS=1` — no
  corre por defecto para no pegarle a Azure real en cada `pytest` local sin avisar):
  lenguaje natural real sin SKU exacto, creación de pedido real que descuenta stock real,
  rechazo de un pedido imposible sin mutar nada, y la tool nueva `find_variant_by_sku`. Una
  corrida mostró una falla puntual no reproducible (el modelo no llamó a `create_order` esa
  vez en particular) — variabilidad real de un LLM real, no un bug: se repitió el mismo
  pedido 3 veces más por separado y las 3 creó el pedido correctamente.
- Probado manualmente con preguntas que el intérprete por regex anterior no podía resolver
  (ej. "cuánto stock tiene el samurai de 10cm sin pintar" sin decir el SKU) — resuelto
  correctamente por el modelo vía tool-calling.

## Trade-offs aceptados

- **Sin historial de conversación entre mensajes**: cada llamada a `/api/agent/chat` es
  independiente (el frontend tampoco manda historial hoy) — el modelo no recuerda
  preguntas anteriores dentro de la misma sesión de chat. Mejora futura, no bloqueante para
  esta sesión.
- **Costo real por mensaje**: cada mensaje del chat es como mínimo una llamada al modelo
  (más una por cada ronda de tool-calling, hasta `_MAX_TOOL_ROUNDS=5`). Capacidad del
  deployment: 10 (`GlobalStandard`) — subir si se nota rate-limiting en uso pesado, mismo
  ajuste que ya documentó `oraculo` para su propio agente.
- **`api-version=2024-10-21` fijo**: se probó a mano contra el recurso real — versiones más
  nuevas devolvían 404 en este momento para este recurso. Revisar si se actualiza el SDK de
  `openai` o el recurso de Foundry.
