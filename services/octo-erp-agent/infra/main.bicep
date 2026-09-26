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

@description('Región de despliegue. Por defecto, la misma del resource group.')
param location string = resourceGroup().location

@description('Nombre base para los recursos nuevos (Function App, Storage Account, App Service Plan, Cosmos DB).')
param baseName string = 'octo-erp'

@description('Nombre de la base de datos de Cosmos DB.')
param cosmosDatabaseName string = 'octo-erp'

@description('Object ids (Entra ID) adicionales a los que se les otorga el rol Cosmos DB Built-in Data Contributor sobre la cuenta — tu usuario para pruebas/desarrollo local y el service principal de OIDC de GitHub Actions para la integración de CI. La identidad administrada de la Function App siempre se agrega, sin necesidad de listarla acá.')
param dataContributorPrincipalIds array = []

@description('Orígenes permitidos por CORS para la API REST (/api/*) que consume apps/web — ver rest_api.py/http_app.py y docs/decisions/007-rest-api-para-apps-web.md. Nota importante: appSettings en Microsoft.Web/sites es un reemplazo completo, no un merge — cualquier origen agregado a mano con `az functionapp config appsettings set` se pierde en el próximo deploy si no está también acá.')
param corsAllowedOrigins string = 'http://localhost:5173,http://localhost:4173'

@description('Connection string de Application Insights para diagnóstico real del worker de Python (logs/exceptions vía az monitor app-insights query) — vacío por defecto. Mismo motivo que corsAllowedOrigins: si se setea a mano con appsettings set en vez de acá, el próximo deploy de este Bicep lo borra.')
@secure()
param applicationInsightsConnectionString string = ''

var uniqueSuffix = uniqueString(resourceGroup().id)
var storageAccountName = toLower('st${replace(baseName, '-', '')}${take(uniqueSuffix, 6)}')
var appServicePlanName = '${baseName}-plan'
var functionAppName = '${baseName}-${take(uniqueSuffix, 6)}'
var cosmosAccountName = toLower('${baseName}-cosmos-${take(uniqueSuffix, 6)}')

// Rol built-in "Cosmos DB Built-in Data Contributor" — lectura/escritura de datos (no de
// control plane). Id fijo documentado por Microsoft, igual en toda cuenta de Cosmos DB.
var cosmosDataContributorRoleId = '00000000-0000-0000-0000-000000000002'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
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
  location: location
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
  location: location
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
        { name: 'WEBSITE_RUN_FROM_PACKAGE', value: '1' }
        { name: 'COSMOS_ENDPOINT', value: cosmosAccount.properties.documentEndpoint }
        { name: 'CORS_ALLOWED_ORIGINS', value: corsAllowedOrigins }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: applicationInsightsConnectionString }
      ]
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
