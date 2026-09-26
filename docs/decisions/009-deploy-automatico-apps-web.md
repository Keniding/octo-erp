# 009 — El sitio público no tenía la sección "Agente": faltaba CD para apps/web

**Estado:** workflow nuevo escrito y pusheado; **bloqueado**, probablemente, en un role
assignment que solo puede correr el dueño de la cuenta (ver "Pendiente de tu lado" —
patrón idéntico al de la decisión 006).

## El síntoma reportado

Después de pushear la sección "Agente" (decisión 008), con CI y CD en verde, el sitio
público (`https://stoctoerpinc.z5.web.core.windows.net/`) seguía sin mostrarla.

## La causa real (verificada, no supuesta)

`octo-erp-agent-cd.yml` es el único workflow de deploy que existía. Su trigger
(`on.push.paths`) solo escucha cambios en `services/octo-erp-agent/**` — y lo que hace es
desplegar `infra/main.bicep` y publicar el código Python (`func azure functionapp publish`)
de la Function App (API + MCP). **En ningún paso construye ni sube `apps/web`.**

Se confirmó revisando el propio Bicep (`infra/main.bicep`): crea el Storage Account
(`stoctoerpinc`) y lee su `primaryEndpoints.web` para calcular el origen de CORS, pero no
habilita el static website hosting ni sube contenido — eso, y cada actualización posterior
del sitio, se hizo a mano (`az storage blob upload-batch`, corrido manualmente en una sesión
anterior). Cuando cambió `apps/web` en esta sesión, nadie volvió a correr ese comando a
mano, y no había ningún pipeline que lo hiciera por su cuenta.

## Decisión

Workflow nuevo, `apps-web-cd.yml`, separado de `octo-erp-agent-cd.yml` (mismo principio de
"cada unidad de despliegue tiene su propio workflow" que ya sigue el propio repo entre CI y
CD, y que sigue Oráculo entre sus dos Function Apps):

1. Trigger en cambios a `apps/web/**` o `packages/**` (el design system y el dominio
   compartido que `apps/web` importa).
2. `npm ci && npm run build:web`, con `VITE_API_BASE_URL` fijado a la URL real ya desplegada
   de la API (`https://octo-erp-inc.azurewebsites.net`) — Vite hornea esta variable en
   tiempo de build, así que tiene que estar seteada ahí, no en runtime.
3. `az storage blob upload-batch` al contenedor `$web` de `stoctoerpinc`, autenticado por
   OIDC (mismo service principal que ya usa `octo-erp-agent-cd.yml`), `--auth-mode login`
   — nunca una account key, mismo principio de "sin keys en ningún lado" que ya rige Cosmos
   DB (decisión 006).

## Por qué separado y no un job más en `octo-erp-agent-cd.yml`

Son dos superficies de cambio independientes con triggers distintos (`apps/web/**` vs.
`services/octo-erp-agent/**`) — meterlos en el mismo workflow dispararía un deploy del
Function App cada vez que cambia solo el frontend (o viceversa), sin necesidad, y
complicaría el `concurrency.group` (que ya es por-workflow, no por-job).

## Pendiente de tu lado (posible bloqueante, a confirmar con el primer run real)

`--auth-mode login` necesita el rol de **datos** `Storage Blob Data Contributor` sobre
`stoctoerpinc` para el mismo service principal de OIDC. El `Contributor` de resource group
que ya tiene (decisión 006) es un rol de **control plane** — alcanza para gestionar el
recurso Storage Account en sí (crearlo, borrarlo, cambiar su config), pero Azure Storage
separa el acceso a blobs vía Entra ID como un plano de datos aparte, igual que ya pasó con
Cosmos DB. Si el primer run de `apps-web-cd.yml` falla con
`AuthorizationPermissionMismatch`, correr:

```bash
az role assignment create \
  --assignee-object-id c6d502e0-76b6-483f-93af-ef65a8002ee5 \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/9b0f2c1e-4e3e-467d-b287-16282ed6a9d7/resourceGroups/rg-octo-erp-dev/providers/Microsoft.Storage/storageAccounts/stoctoerpinc"
```

(mismo `principal-id` que ya se usó en decisión 006 para los otros dos role assignments —
es el mismo service principal de CI, `gh-octo-erp-agent-ci`). No se ejecuta desde acá por el
mismo motivo que las dos asignaciones anteriores: otorgar permisos queda fuera de lo que
este entorno corre de forma autónoma.

## Otro hallazgo en el camino: CI no corría dos archivos de test

`octo-erp-agent-ci.yml`, job `unit-tests`, listaba los archivos de test a mano
(`test_service.py test_mcp_server.py test_repositories_conform_to_protocol.py`) — quedó
desactualizado y **nunca corrió** `test_rest_api.py` (de la sesión anterior) ni
`test_agent_chat.py` (decisión 008) a pesar de que el check se veía en verde. Corregido a
`uv run pytest --ignore=tests/test_cosmos_integration.py -v`, que corre todo lo que no
necesita Azure sin tener que acordarse de listar cada archivo nuevo.
