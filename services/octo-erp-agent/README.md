# octo-erp-agent — dominio + MCP custom para el agente de IA de Octo ERP

Implementación real (no solo especificación) del MCP custom descrito en
`oraculo/docs/10-especificacion-2-agente-octo-erp.md` (sección 10.7) y
[`docs/decisions/004-agente-ia-mcp-cosmosdb.md`](../../docs/decisions/004-agente-ia-mcp-cosmosdb.md).

## Qué está probado de verdad y qué no

| Capa | Estado |
|---|---|
| `domain/service.py` (reglas de negocio: validación de stock, creación de pedidos, umbrales de reposición) | ✅ 17 tests unitarios reales, corriendo contra `InMemoryRepository` — `tests/test_service.py` |
| `mcp_server.py` (servidor MCP completo: tools, protocolo) | ✅ 1 test end-to-end real: levanta un servidor HTTP de verdad (uvicorn) y le habla con el **cliente MCP oficial** (`mcp.client.streamable_http` + `ClientSession`) — `tests/test_mcp_server.py`. No es un mock: es `initialize` → `tools/list` → `tools/call` real sobre HTTP real. |
| `repositories/cosmos.py` (conexión real a Azure Cosmos DB) | ✅ Verificado contra una cuenta real (`rg-octo-erp-dev`, Serverless, 5 containers) — `tests/test_cosmos_integration.py`, 4 tests de round-trip real, autenticados por RBAC de datos de Entra ID (sin keys). Ver [decisión 006](../../docs/decisions/006-ci-cd-azure-oidc.md). También probado que implementa el mismo contrato que `InMemoryRepository` (`tests/test_repositories_conform_to_protocol.py`). |
| Despliegue en Azure Functions | ✅ `infra/main.bicep` desplegado + `function_app.py` (wrapper, mismo patrón que `oraculo/function_app.py`) + CI/CD en GitHub Actions (`.github/workflows/octo-erp-agent-{ci,cd}.yml`) con auth OIDC. Bloqueado en dos asignaciones de rol que quedan para que el dueño de la cuenta las corra — ver decisión 006, "Pendiente de tu lado". |
| Auth Entra ID/Easy Auth de cara al agente/Foundry | ❌ No implementado todavía — pendiente el proyecto de ejemplo del usuario para el mecanismo exacto (ver especificación, sección 10.9). |

## Correr los tests

```bash
cd services/octo-erp-agent
uv sync
uv run pytest -v
```

20 tests unitarios/MCP, determinísticos, sin red externa (el test end-to-end del MCP levanta
su propio servidor en un puerto local libre y lo cierra al terminar), + 4 tests de
integración real contra Cosmos DB que se saltan automáticamente si no hay `COSMOS_ENDPOINT`
en el entorno. Para correr esos 4 contra la cuenta real de `rg-octo-erp-dev` (con `az login`
ya autenticado y el rol de datos asignado a tu usuario):

```bash
COSMOS_ENDPOINT="https://octo-erp-cosmos-hrhdi4.documents.azure.com:443/" uv run pytest tests/test_cosmos_integration.py -v
```

En CI, esto mismo corre autenticado por OIDC en vez de tu `az login` — ver
`.github/workflows/octo-erp-agent-ci.yml` y la [decisión 006](../../docs/decisions/006-ci-cd-azure-oidc.md).

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
