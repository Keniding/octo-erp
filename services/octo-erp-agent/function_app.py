"""Azure Function (Consumption/serverless) que hospeda el servidor MCP custom de Octo ERP
(`/mcp`, para el agente de IA/Foundry) y la API REST para apps/web/apps/mobile (`/api/*`).

Mismo patrón que oraculo/function_app.py: la app ASGI combinada se construye una sola vez en
`src/octo_erp_agent/http_app.py` — este archivo solo la envuelve para que Azure Functions la
sirva. Con `COSMOS_ENDPOINT` seteado como app setting (ver infra/main.bicep), ambas rutas
usan CosmosRepository autenticado por la identidad administrada de esta Function App, nunca
por connection string ni key.

Deploy: ver infra/main.bicep (recursos) y .github/workflows/octo-erp-agent-cd.yml (pipeline).
"""

import azure.functions as func

from octo_erp_agent.http_app import asgi_app

app = func.AsgiFunctionApp(app=asgi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
