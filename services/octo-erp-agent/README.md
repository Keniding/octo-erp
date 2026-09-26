# octo-erp-agent — dominio + MCP custom para el agente de IA de Octo ERP

Implementación real (no solo especificación) del MCP custom descrito en
`oraculo/docs/10-especificacion-2-agente-octo-erp.md` (sección 10.7) y
[`docs/decisions/004-agente-ia-mcp-cosmosdb.md`](../../docs/decisions/004-agente-ia-mcp-cosmosdb.md).

## Qué está probado de verdad y qué no

| Capa | Estado |
|---|---|
| `domain/service.py` (reglas de negocio: validación de stock, creación de pedidos, umbrales de reposición) | ✅ 17 tests unitarios reales, corriendo contra `InMemoryRepository` — `tests/test_service.py` |
| `mcp_server.py` (servidor MCP completo: tools, protocolo) | ✅ 1 test end-to-end real: levanta un servidor HTTP de verdad (uvicorn) y le habla con el **cliente MCP oficial** (`mcp.client.streamable_http` + `ClientSession`) — `tests/test_mcp_server.py`. No es un mock: es `initialize` → `tools/list` → `tools/call` real sobre HTTP real. |
| `repositories/cosmos.py` (conexión real a Azure Cosmos DB) | ⚠️ Código escrito contra la API real del SDK `azure-cosmos`, pero **sin verificar contra una cuenta de Cosmos DB real** — este sandbox no tiene credenciales de Azure. Sí está probado que implementa el mismo contrato que `InMemoryRepository` (`tests/test_repositories_conform_to_protocol.py`). |
| Despliegue en Azure Functions, auth Entra ID/Easy Auth | ❌ No implementado todavía — eso vive en Bicep, pendiente (ver especificación, sección 10.11). |

## Correr los tests

```bash
cd services/octo-erp-agent
uv sync
uv run pytest -v
```

20 tests, todos determinísticos, sin red externa (el test end-to-end del MCP levanta su
propio servidor en un puerto local libre y lo cierra al terminar).

## Correr el servidor MCP localmente

```bash
uv run python -m octo_erp_agent.mcp_server
# sirve en http://0.0.0.0:8000/mcp, con datos semilla en memoria (mismos que
# packages/shared/src/seed.ts)
```

Con `COSMOS_ENDPOINT` seteado en `.env` (ver `.env.example`), usa Cosmos DB real en vez de
memoria — para eso primero hay que crear la cuenta y los containers, por ejemplo:

```python
from octo_erp_agent.repositories.cosmos import CosmosRepository
CosmosRepository.provision_database("https://<tu-cuenta>.documents.azure.com:443/")
```

## Fuente de verdad — decisión ya tomada

Cosmos DB **es** la fuente de verdad única (no una réplica solo para el agente) — decisión
confirmada, ver `docs/decisions/004-agente-ia-mcp-cosmosdb.md` (sección actualizada) y
`docs/decisions/005-cache-frontend-vs-fuente-de-verdad.md` para cómo encaja esto con
`apps/web`/`apps/mobile` (caché en el frontend solo para preferencias y lazy loading, nunca
como fuente de verdad).

Este paquete (`domain/`, `repositories/`) es el candidato natural para, más adelante, ser
también el backend real de `packages/shared` — hoy `packages/shared/src/store.ts` (TS, en
memoria) y este paquete (Python, contra Cosmos DB) implementan **las mismas reglas de
negocio en paralelo**, deliberadamente casi línea por línea, para que migrar
`apps/web`/`apps/mobile` a consumir una API respaldada por este paquete no requiera
reinterpretar ninguna regla.
