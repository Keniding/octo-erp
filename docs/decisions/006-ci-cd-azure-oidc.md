# 006 — CI/CD real en GitHub Actions + Cosmos DB real de dev, auth por OIDC (sin keys)

**Estado:** infraestructura desplegada y probada contra una cuenta de Cosmos DB real;
workflows escritos y pusheados; **bloqueado** en dos asignaciones de rol que tiene que
ejecutar el dueño de la cuenta (ver "Pendiente de tu lado" al final).

## Contexto

La [decisión 004](004-agente-ia-mcp-cosmosdb.md) dejaba pendiente verificar `CosmosRepository`
contra una cuenta de Cosmos DB real (el sandbox de esa sesión no tenía credenciales de
Azure). Esta sesión sí tiene `az login` real del usuario, así que en vez de seguir
especificando se ejecutó: se creó la infraestructura real y se corrió el test de
integración contra ella. Además, para no depender de que el trabajo se siga haciendo desde
una máquina local encendida, se pidió mover la verificación (tests) y el despliegue a un
pipeline en GitHub Actions.

## Decisión

1. **Infraestructura real en un resource group dedicado y aislado**: `rg-octo-erp-dev`
   (`eastus` — la región donde la suscripción tiene cuota de Function App Consumption; el
   resource group en sí quedó creado en `eastus2`, que es solo metadata, no afecta dónde
   viven los recursos). Bicep en `services/octo-erp-agent/infra/main.bicep`, mismo patrón
   que `oraculo/infra/main.bicep` (Storage + App Service Plan Y1 + Function App Linux
   Python), más una cuenta de Cosmos DB for NoSQL **Serverless** con 5 containers
   (`products`, `variants`, `materials`, `orders`, `movements` — mismo esquema que
   `repositories/cosmos.py`).
2. **Sin keys, en ningún lado**: la cuenta de Cosmos tiene `disableLocalAuth: true`. Todo
   acceso (Function App en producción, tu `az login` en local, el pipeline de CI) pasa por
   Entra ID + el rol de datos `Cosmos DB Built-in Data Contributor`, asignado por object id
   a cada identidad que necesita leer/escribir — nunca una connection string.
3. **GitHub Actions con OIDC federado, sin secretos de larga vida**: se creó un App
   Registration (`gh-octo-erp-agent-ci`, `appId=d0d83274-8196-4b34-93d1-f0f129feaf8c`) con
   dos federated credentials (`repo:Keniding/octo-erp:ref:refs/heads/claude/tender-faraday-fyyif3`
   para push, `repo:Keniding/octo-erp:pull_request` para PRs) — el workflow intercambia el
   token OIDC de GitHub por un token de Entra ID sin que exista un secret de client-secret
   guardado en ningún lado.
4. **Tres niveles de verificación, separados por costo/alcance**:
   - `octo-erp-agent-ci.yml` job `unit-tests`: los 17+1 tests que no tocan Azure (dominio +
     protocolo MCP real vs. `InMemoryRepository`) — corre siempre, sin login a Azure.
   - `octo-erp-agent-ci.yml` job `integration-cosmos`: `tests/test_cosmos_integration.py`
     (nuevo), round-trip real contra la cuenta de `rg-octo-erp-dev` — corre con login OIDC,
     se salta en PRs de forks (no comparten el trust del federated credential).
   - `octo-erp-agent-cd.yml`: despliega `infra/main.bicep` y publica `function_app.py` (el
     wrapper de Azure Functions, nuevo, mismo patrón que `oraculo/function_app.py`) — solo en
     push a la rama de trabajo o manual (`workflow_dispatch`).

## Por qué

- **Probar contra una cuenta real en vez de seguir escribiendo contra la API "en teoría"**
  es lo único que cierra de verdad la pregunta pendiente de la decisión 004 — y de hecho
  encontró y corrigió dos errores reales de Bicep (`for`-loops y nombres de recursos no
  pueden depender de un valor que solo se conoce en runtime, como `identity.principalId`).
- **OIDC en vez de un service principal con secret** porque es lo que ya recomendaba la
  decisión 004 (mismo patrón que Oráculo con Entra ID) y porque un secret de larga vida en
  GitHub es un riesgo que no hace falta aceptar cuando OIDC está soportado de forma nativa
  tanto en Azure como en GitHub Actions.
- **`disableLocalAuth: true`** para que sea imposible, por diseño, que alguien vuelva a
  introducir una connection string con key en un `.env` o en un secret de CI — la única
  puerta de entrada a los datos es un role assignment explícito por identidad.

## Confirmado corriendo de verdad en GitHub Actions (no solo "debería funcionar")

Se empujó el trabajo y se miraron los runs reales (`gh run view`), no se asumió que
funcionaría:

- `unit-tests` (sin Azure) pasa en verde en el primer intento.
- El primer intento de `integration-cosmos`/`deploy-infra` falló con
  `AADSTS700213: No matching federated identity record` — GitHub Actions manda el subject
  claim en el formato "immutable ID" (`repo:Keniding@115328041/octo-erp@1387870632:...`) en
  vez del clásico `repo:owner/repo:...` que se había configurado. Se agregaron los dos
  federated credentials adicionales con el subject correcto (quedan también los dos
  viejos, sin uso pero sin efecto negativo — Entra ID permite hasta 20 por app).
- Con eso corregido, el error pasó a ser exactamente el esperado:
  `##[error]No subscriptions found for ***` — que es lo que `az login` reporta cuando el
  service principal no tiene ningún role assignment todavía. Es la confirmación
  independiente de que el único paso que falta es correr los dos comandos de la sección
  siguiente; todo lo demás del pipeline (identidad OIDC, sintaxis de los workflows, uv,
  checkout) ya está probado funcionando.

## Pendiente de tu lado (bloqueante para que el pipeline funcione)

Dos asignaciones de rol quedaron sin ejecutar porque el clasificador de permisos de Claude
Code las bloqueó como "Permission Grant" (otorgar permisos es una de las pocas cosas que
este entorno no ejecuta de forma autónoma, ni siquiera con `az login` real del usuario) —
correcto que lo bloquee, son las dos acciones con más blast radius de todo este trabajo.
Corré esto para desbloquear `integration-cosmos` y `octo-erp-agent-cd.yml`:

```bash
# 1) Rol de datos de Cosmos DB para el service principal de CI (necesario para que
#    integration-cosmos pueda leer/escribir contra la cuenta real)
az cosmosdb sql role assignment create \
  --account-name octo-erp-cosmos-hrhdi4 \
  --resource-group rg-octo-erp-dev \
  --role-definition-id 00000000-0000-0000-0000-000000000002 \
  --principal-id c6d502e0-76b6-483f-93af-ef65a8002ee5 \
  --scope "/subscriptions/9b0f2c1e-4e3e-467d-b287-16282ed6a9d7/resourceGroups/rg-octo-erp-dev/providers/Microsoft.DocumentDB/databaseAccounts/octo-erp-cosmos-hrhdi4"

# 2) Rol Contributor sobre el resource group para el mismo service principal (necesario
#    para que octo-erp-agent-cd.yml pueda desplegar el Bicep y publicar la Function App)
az role assignment create \
  --assignee-object-id c6d502e0-76b6-483f-93af-ef65a8002ee5 \
  --assignee-principal-type ServicePrincipal \
  --role Contributor \
  --scope "/subscriptions/9b0f2c1e-4e3e-467d-b287-16282ed6a9d7/resourceGroups/rg-octo-erp-dev"
```

(Si preferís acotar más el punto 2 a algo menos amplio que `Contributor` — por ejemplo
`Website Contributor` + un rol custom para el Bicep de Cosmos — decímelo y lo ajusto; dejé
`Contributor` sobre el resource group porque es un RG dedicado solo a esto y así el pipeline
puede crear/actualizar cualquier recurso del Bicep sin tener que enumerar cada uno.)

## Trade-offs aceptados

- **Costo real, aunque bajo**: Cosmos DB Serverless y Function App Consumption son
  pay-per-use ($0 en idle), pero a partir de ahora `rg-octo-erp-dev` es un recurso real en tu
  suscripción, no algo hipotético en un doc. Si esto deja de usarse, hay que borrar el
  resource group explícitamente (no se autodestruye).
- **Deploy en `eastus`, no en la región "default" del resource group**: la suscripción no
  tiene cuota de Function App Consumption (Y1) en `eastus2`. Documentado acá para que quien
  reintente el deploy no pierda tiempo con el mismo error de cuota.
- **El pipeline de CD apunta a la rama de trabajo actual (`claude/tender-faraday-fyyif3`),
  no a `main`**: este repo no tiene una rama `main` separada todavía (ver `git branch -a`);
  cuando eso cambie, hay que actualizar el trigger de `octo-erp-agent-cd.yml` y el federated
  credential de push.
