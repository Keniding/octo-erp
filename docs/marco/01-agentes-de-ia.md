# 1. Agentes de IA

## Qué NO es un agente

Antes de definir "agente" conviene descartar dos cosas con las que se confunde todo el
tiempo:

- **Una función determinista no es un agente.** Si un problema se puede resolver con
  `if`/`match`/una expresión regular, escribir eso — no un agente — es la solución correcta.
  El propio Microsoft Agent Framework lo dice explícito en su documentación: *"si podés
  escribir una función normal para resolver la tarea, hacelo — no uses un agente de IA"*.
  Este proyecto tuvo, de hecho, las dos versiones de la misma funcionalidad en momentos
  distintos: primero un intérprete de comandos por regex (determinista, rápido, gratis,
  cero variabilidad), después un agente real (ver `docs/decisions/008` y `010`) — la
  diferencia entre ambos es exactamente esta línea.
- **Una sola llamada a un LLM tampoco es un agente**, aunque el LLM sea excelente. Si el
  flujo es "prompt de entrada → una respuesta de texto → fin", es una función de IA, no un
  agente — no hay ciclo de decisión, no hay acción sobre el mundo.

## Qué es un agente

Un **agente** es un sistema que, dado un objetivo, **decide autónomamente qué hacer paso a
paso** — incluyendo qué herramientas usar, en qué orden, y cuándo considerar terminada la
tarea — en vez de seguir un camino de ejecución fijado de antemano por el programador. La
pieza que decide es un modelo de lenguaje; las piezas que ejecutan son **tools** (funciones
reales con efectos reales: leer una base de datos, crear un pedido, mandar un email).

### El loop del agente

Todo agente, sin importar el framework, implementa una variación del mismo ciclo:

```
1. El agente recibe un objetivo/mensaje.
2. El modelo decide: ¿responde directamente, o necesita llamar una tool?
3. Si necesita una tool: la ejecuta, observa el resultado.
4. Vuelve al paso 2 con el resultado incorporado al contexto — hasta que decide que ya
   puede responder en texto plano (o hasta un límite de "rondas" para evitar loops
   infinitos).
5. Devuelve la respuesta final.
```

Este ciclo (razonar → actuar → observar → repetir) es el patrón **ReAct** (*Reasoning +
Acting*), el diseño de agente más extendido hoy — es literalmente lo que implementa
`services/octo-erp-agent/src/octo_erp_agent/agent_chat.py` a mano, sin ningún framework de
agentes: un `for` que llama al modelo, revisa si pidió `tool_calls`, los ejecuta, y vuelve a
llamar al modelo con el resultado — hasta que el modelo responde en texto.

### Tool-calling (function calling)

El mecanismo que conecta al modelo con el mundo real. El flujo, a nivel de API:

1. Junto con el mensaje, se le manda al modelo una lista de **tools disponibles**: nombre,
   descripción en lenguaje natural, y un JSON Schema de los parámetros que acepta.
2. El modelo, en vez de responder en texto, puede responder con una **intención de llamada**
   (`tool_calls`): qué tool quiere invocar y con qué argumentos — el modelo *nunca ejecuta
   nada él mismo*, solo pide.
3. El programa (no el modelo) ejecuta la tool de verdad, contra un sistema real.
4. El resultado de la tool se agrega a la conversación como un mensaje de rol `tool`, y se
   vuelve a llamar al modelo — que ahora puede responder en texto usando ese resultado, o
   pedir otra tool.

La calidad de un agente depende casi por completo de la calidad de las **descripciones** de
las tools (qué hace, qué devuelve, cuándo usarla) — es la única "documentación" que el
modelo tiene para decidir, no ve el código.

### Autonomía: espectro, no binario

"Agente" no es una categoría única — hay un espectro de autonomía:

- **Un solo tool-call por turno**, siempre bajo supervisión humana antes de confirmar
  acciones sensibles (*human-in-the-loop* — en Microsoft Agent Framework, por ejemplo,
  `ApprovalRequiredAIFunction`).
- **Varias rondas de tool-calling** dentro de un mismo turno (lo que hace este proyecto,
  hasta `_MAX_TOOL_ROUNDS`), sin supervisión intermedia, pero con las reglas de negocio
  (`domain/service.py`) como última línea de defensa — el modelo puede *pedir* un pedido
  imposible, pero nunca puede *forzar* que se cree.
- **Planificación multi-paso autónoma**, donde el propio agente decide la secuencia de
  varias tareas grandes sin que el humano defina los pasos — el extremo más autónomo, y el
  que más beneficia de **orquestación explícita** (sección 3) para no perder control.

## Por qué esto importa para el negocio (y no es solo una moda técnica)

Un intérprete de comandos exige que el usuario aprenda la sintaxis exacta ("pedido SKU x2
para Cliente"). Un agente real entiende "necesito pedir dos del samurái sin pintar para el
taller Origami" — la diferencia no es cosmética, es la diferencia entre una herramienta que
solo usa quien ya sabe el sistema, y una que cualquiera puede usar hablándole normal. Esa es
la razón de negocio real detrás de la decisión 010 de este proyecto — no "usar IA porque
sí", sino bajar la barrera de entrada al sistema.
