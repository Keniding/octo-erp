"""Azure Function (Consumption/serverless) que hospeda el servidor MCP custom de Octo ERP.

Mismo patrón que oraculo/function_app.py: la app ASGI (con streamable-http, seguridad de
transporte y el rechazo de GET/SSE) se construye una sola vez en
`src/octo_erp_agent/mcp_server.py` — este archivo solo la envuelve para que Azure Functions
la sirva. Con `COSMOS_ENDPOINT` seteado como app setting (ver infra/main.bicep), usa
CosmosRepository autenticado por la identidad administrada de esta Function App, nunca por
connection string ni key.

Deploy: ver infra/main.bicep (recursos) y .github/workflows/octo-erp-agent-cd.yml (pipeline).
"""

import azure.functions as func

from octo_erp_agent.mcp_server import asgi_app

app = func.AsgiFunctionApp(app=asgi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
