// Infraestructura para el agente de IA + MCP custom de Octo ERP (services/octo-erp-agent).
// Mismo patrón que oraculo/infra/main.bicep (Function App Consumption + AsgiFunctionApp),
// más Cosmos DB for NoSQL en modo Serverless como única fuente de verdad de datos de
// negocio (ver docs/decisions/004-agente-ia-mcp-cosmosdb.md y 005-cache-frontend-vs-fuente-de-verdad.md).
//
// Auth de datos: sin keys. disableLocalAuth=true en la cuenta de Cosmos — todo acceso
// (Function App en producción, tu `az login` en local, el pipeline de CI) pasa por Entra ID
// + un role assignment de datos de Cosmos DB (Data Contributor), nunca por connection string.
//
// Deploy:
//   az deployment group create -g rg-octo-erp-dev -f infra/main.bicep \
//     -p dataContributorPrincipalIds="['<tu-object-id>','<object-id-del-service-principal-de-CI>']"

@description('Región de Cosmos DB. Por defecto, la misma del resource group. No cambiar una vez creada la cuenta — Cosmos DB no permite recrearla con el mismo nombre en otra región.')
param location string = resourceGroup().location

@description('Región de los recursos de cómputo (Storage, App Service Plan, Function App) — separada de `location` porque hubo un problema de plataforma específico de `eastus` para esta suscripción con el sync-trigger de Function Apps Python en Consumption (ver docs/decisions/007-rest-api-para-apps-web.md): la Function App se movió a otra región sin tener que recrear Cosmos DB. Por defecto, igual a `location`.')
param computeLocation string = location

@description('Nombre base para Cosmos DB (no tocar — cambia el nombre de la cuenta existente con los datos ya sembrados).')
param baseName string = 'octo-erp'

@description('Nombre exacto de la Function App. Fijo en vez de autogenerado con hash — ver docs/decisions/007-rest-api-para-apps-web.md, "El deploy no era reproducible/determinístico": redesplegar código es confiable, pero cambiar un app setting justo antes de un deploy dispara fallas intermitentes de sync-trigger en esta suscripción, y una vez que falla contra un nombre, ese nombre tiende a seguir fallando. `octo-erp-inc` es el nombre bajo el que se confirmó, con un despliegue incremental controlado, que todo (REST + MCP + Cosmos + CORS hardcodeado en código) funciona de punta a punta — no renombrar sin necesidad, y evitar tocar app settings salvo que sea imprescindible.')
param functionAppName string = 'octo-erp-inc'

@description('Nombre exacto del Storage Account que respalda la Function App de arriba.')
param storageAccountNameOverride string = 'stoctoerpinc'

@description('Nombre de la base de datos de Cosmos DB.')
param cosmosDatabaseName string = 'octo-erp'

@description('Object ids (Entra ID) adicionales a los que se les otorga el rol Cosmos DB Built-in Data Contributor sobre la cuenta — tu usuario para pruebas/desarrollo local y el service principal de OIDC de GitHub Actions para la integración de CI. La identidad administrada de la Function App siempre se agrega, sin necesidad de listarla acá.')
param dataContributorPrincipalIds array = []

var uniqueSuffix = uniqueString(resourceGroup().id)
var storageAccountName = storageAccountNameOverride
var appServicePlanName = '${functionAppName}-plan'
var cosmosAccountName = toLower('${baseName}-cosmos-${take(uniqueSuffix, 6)}')
// primaryEndpoints.web viene con "/" final (ej. "https://foo.z5.web.core.windows.net/");
// un origen de CORS no lleva esa barra — bicep no tiene trimEnd, así que se recorta a mano.
var staticWebsiteEndpoint = storageAccount.properties.primaryEndpoints.web
var staticWebsiteOrigin = substring(staticWebsiteEndpoint, 0, length(staticWebsiteEndpoint) - 1)

// Rol built-in "Cosmos DB Built-in Data Contributor" — lectura/escritura de datos (no de
// control plane). Id fijo documentado por Microsoft, igual en toda cuenta de Cosmos DB.
var cosmosDataContributorRoleId = '00000000-0000-0000-0000-000000000002'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: computeLocation
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: computeLocation
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  kind: 'functionapp'
  properties: {
    reserved: true // Linux
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: computeLocation
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      appSettings: [
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'AzureWebJobsStorage', value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}' }
        // NO pre-setear WEBSITE_RUN_FROM_PACKAGE=1 acá — causa real encontrada y probada
        // (ver docs/decisions/007-rest-api-para-apps-web.md): con este setting ya presente,
        // tanto `func azure functionapp publish` como Azure/functions-action usan el modo
        // "Run From Package" vía blob+SAS, que falló consistentemente en el sync-trigger
        // (6+ intentos, 3 mecanismos de deploy, incluso en Function Apps recién creadas).
        // Sin este setting, el deploy hace un build remoto completo (Oryx/squashfs) y el
        // sync-trigger funciona al instante — confirmado en 2/2 pruebas. El deploy es quien
        // gestiona este setting dinámicamente, no la infra.
        // CORS_ALLOWED_ORIGINS y APPLICATIONINSIGHTS_CONNECTION_STRING deliberadamente NO
        // están acá — ver docs/decisions/007-rest-api-para-apps-web.md, "El deploy no era
        // reproducible/determinístico": cambiar CUALQUIER app setting justo antes de un
        // deploy dispara fallas intermitentes de sync-trigger en esta suscripción (3/3
        // fallos reproducidos). El origen de CORS del sitio estático quedó hardcodeado en
        // código (http_app.py, _DEFAULT_CORS_ORIGINS) — un cambio de código, no de config,
        // que sí es confiable. Si hace falta Application Insights de nuevo para
        // diagnóstico, configurarlo a mano vía `az functionapp config appsettings set` y
        // asumir que el próximo deploy de este Bicep no lo va a tocar (no está en esta
        // lista), pero que el próximo *cambio de config* después de eso puede requerir
        // varios intentos de redeploy de código para asentarse.
        { name: 'COSMOS_ENDPOINT', value: cosmosAccount.properties.documentEndpoint }
      ]
      // CORS de PLATAFORMA (distinto del CORSMiddleware de Starlette en http_app.py) — el
      // OPTIONS de un preflight real de browser nunca llega al código Python: Azure
      // Functions lo intercepta y responde él mismo, y sin esto configurado responde un
      // 204 vacío sin headers de CORS, lo que hace que el browser bloquee la request real
      // ("Failed to fetch"). Confirmado con curl -v contra el preflight real. No es lo
      // mismo que _DEFAULT_CORS_ORIGINS en http_app.py — hacen falta los dos: éste para que
      // el preflight OPTIONS pase, el de Starlette para los headers en la respuesta real.
      cors: {
        allowedOrigins: [
          'http://localhost:5173'
          'http://localhost:4173'
          staticWebsiteOrigin
        ]
      }
    }
  }
}

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-08-15' = {
  name: cosmosAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      { locationName: location, failoverPriority: 0 }
    ]
    capabilities: [
      { name: 'EnableServerless' }
    ]
    disableLocalAuth: true
    minimalTlsVersion: 'Tls12'
  }
}

resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-08-15' = {
  parent: cosmosAccount
  name: cosmosDatabaseName
  properties: {
    resource: {
      id: cosmosDatabaseName
    }
  }
}

// Containers y partition keys — mismo esquema que repositories/cosmos.py.
resource containerProducts 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-08-15' = {
  parent: cosmosDatabase
  name: 'products'
  properties: {
    resource: { id: 'products', partitionKey: { paths: ['/id'], kind: 'Hash' } }
  }
}

resource containerVariants 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-08-15' = {
  parent: cosmosDatabase
  name: 'variants'
  properties: {
    resource: { id: 'variants', partitionKey: { paths: ['/productId'], kind: 'Hash' } }
  }
}

resource containerMaterials 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-08-15' = {
  parent: cosmosDatabase
  name: 'materials'
  properties: {
    resource: { id: 'materials', partitionKey: { paths: ['/id'], kind: 'Hash' } }
  }
}

resource containerOrders 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-08-15' = {
  parent: cosmosDatabase
  name: 'orders'
  properties: {
    resource: { id: 'orders', partitionKey: { paths: ['/id'], kind: 'Hash' } }
  }
}

resource containerMovements 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-08-15' = {
  parent: cosmosDatabase
  name: 'movements'
  properties: {
    resource: { id: 'movements', partitionKey: { paths: ['/targetId'], kind: 'Hash' } }
  }
}

// Role assignments de datos de Cosmos DB (no son Microsoft.Authorization/roleAssignments
// genéricos — Cosmos DB tiene su propio sistema de RBAC a nivel de datos). El for-loop solo
// puede iterar sobre valores conocidos al inicio del deployment, así que la identidad
// administrada de la Function App (conocida solo en runtime) se asigna en un recurso aparte.
resource dataContributorAssignments 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-08-15' = [
  for principalId in dataContributorPrincipalIds: {
    parent: cosmosAccount
    name: guid(cosmosAccount.id, principalId, cosmosDataContributorRoleId)
    properties: {
      roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${cosmosDataContributorRoleId}'
      principalId: principalId
      scope: cosmosAccount.id
    }
  }
]

resource functionAppDataContributorAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-08-15' = {
  parent: cosmosAccount
  // El nombre del role assignment debe ser calculable al inicio del deployment, así que se
  // deriva de functionAppName (conocido) en vez del principalId (solo conocido en runtime).
  name: guid(cosmosAccount.id, functionAppName, cosmosDataContributorRoleId)
  properties: {
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${cosmosDataContributorRoleId}'
    principalId: functionApp.identity.principalId
    scope: cosmosAccount.id
  }
}

@description('Endpoint de Cosmos DB (para COSMOS_ENDPOINT en .env o secrets de CI).')
output cosmosEndpoint string = cosmosAccount.properties.documentEndpoint

@description('Nombre de la cuenta de Cosmos DB.')
output cosmosAccountName string = cosmosAccount.name

@description('URL completa a usar como MCP_SERVER_URL (routePrefix="" en host.json).')
output mcpServerUrl string = 'https://${functionApp.properties.defaultHostName}/mcp'

@description('Nombre de la Function App (para el deploy de código vía GitHub Actions).')
output functionAppName string = functionApp.name
