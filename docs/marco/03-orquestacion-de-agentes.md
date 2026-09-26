# 3. Orquestación de agentes

## De un agente a varios

Todo lo visto en la sección 1 describe **un** agente con **tools**. Eso alcanza para mucho
— es exactamente lo que implementa este proyecto — pero hay una categoría de problemas donde
un solo agente, con un solo prompt de sistema y un solo catálogo de tools, deja de ser el
diseño correcto: cuando la tarea tiene **fases con objetivos distintos**, o se beneficia de
**puntos de vista independientes** que después se combinan. Ahí aparece la **orquestación
multi-agente**: coordinar varios agentes (cada uno más simple y enfocado que uno solo que
intente hacer todo) según un patrón explícito.

Microsoft Agent Framework (sección 5) formaliza esta distinción con una tabla de decisión
muy directa:

| Usá un **Agente** cuando… | Usá un **Workflow** (orquestación) cuando… |
|---|---|
| La tarea es abierta y conversacional | El proceso tiene pasos bien definidos |
| Basta una sola llamada al LLM (con o sin tools) | Varios agentes deben coordinarse en un orden |
| No hace falta control explícito del flujo | Sí hace falta control explícito del flujo |

## Los patrones de orquestación más usados

- **Secuencial**: el agente A termina, su salida es la entrada del agente B, y así — una
  cadena de montaje. Útil cuando cada fase necesita un prompt/contexto/set de tools distinto
  (ej.: un agente que extrae datos de un documento → un agente que los valida → un agente
  que redacta un resumen).
- **Concurrente (fan-out/fan-in)**: varios agentes atacan el mismo problema en paralelo,
  desde ángulos distintos, y un paso final combina los resultados — útil para obtener
  "segundas opiniones" independientes antes de decidir.
- **Handoff**: un agente decide, en medio de la conversación, pasarle el control a otro
  agente más especializado (ej.: un agente de atención general que deriva a un agente de
  facturación específico cuando detecta esa intención) — el usuario sigue en la misma
  conversación, pero el agente que responde cambia.
- **Group chat / debate**: varios agentes participan de la misma conversación, cada uno con
  su rol, y se turnan — útil para simular una revisión por pares o un comité.
- **Planificador + workers (magentic)**: un agente "planificador" descompone la tarea en
  subtareas y las delega a agentes "worker" especializados, después integra sus resultados
  — el patrón más autónomo, y el que más necesita límites explícitos (cuántos pasos,
  cuándo parar, qué puede hacer cada worker) para no perder control del costo ni del
  comportamiento.

## Por qué la orquestación se modela como grafo

Los frameworks maduros (Microsoft Agent Framework incluido) modelan estos patrones como un
**grafo de ejecutores conectados por aristas**, no como código imperativo con `if`s
anidados. La razón: un grafo explícito se puede *inspeccionar*, *versionar*, *dibujar*, y
*probar en partes* — algo que un multi-agente escrito como una cadena de llamadas anidadas
en código imperativo pierde apenas crece. En MAF concretamente: cada agente (o función) es
un **`Executor`**, cada posible transición es una **arista** (`edge`), y el conjunto es un
**`Workflow`** con eventos y (opcionalmente) *checkpointing* — poder pausar y reanudar la
ejecución del grafo en el medio.

## Dónde encaja este proyecto en este mapa

`agent_chat.py`, hoy, es un **agente único** (sección 1), no una orquestación — no hay
grafo, no hay varios agentes con roles distintos, no hay handoff. Es la elección correcta
para el problema que resuelve: consultar/ajustar datos de un ERP no tiene fases con
objetivos independientes que se beneficien de agentes separados — un solo agente con un
catálogo de tools bien descriptas alcanza. La sección 7 vuelve sobre esto con más
precisión: qué patrón de los de esta sección tendría sentido si el alcance creciera (por
ejemplo, un agente de "atención al cliente" que hace *handoff* a este agente de operaciones
cuando detecta una intención transaccional).
