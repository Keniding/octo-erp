"""ASGI combinado: servidor MCP custom (`/mcp`, para el agente de IA/Foundry) + API REST
(`/api/*`, para apps/web/apps/mobile) en el mismo proceso y el mismo despliegue de Azure
Functions — ver docs/decisions/007-rest-api-para-apps-web.md.

Ambos comparten la misma instancia de repositorio (`mcp_server.repo`), así que ven
exactamente los mismos datos — no hay una segunda conexión a Cosmos DB ni un segundo
InMemoryRepository con estado separado.
"""

from __future__ import annotations

import os

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from . import mcp_server
from .rest_api import api_routes

# Sin auth todavía en esta API (ver docs/decisions/007-rest-api-para-apps-web.md, "Pendiente"
# — la protección real hoy es la misma que ya documentaba mcp_server.py para /mcp: capa de
# hosting, no esta capa de aplicación). Por eso el origen permitido es explícito y acotado a
# los puertos de dev de Vite en vez de "*" — cualquier despliegue real de apps/web agrega su
# origen acá vía CORS_ALLOWED_ORIGINS.
_DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,http://localhost:4173,"
    "https://stoctoerpinc.z5.web.core.windows.net"
)
_cors_origins = [
    o.strip()
    for o in os.environ.get("CORS_ALLOWED_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if o.strip()
]

asgi_app = Starlette(
    routes=[*api_routes, Mount("/", app=mcp_server.asgi_app)],
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=_cors_origins,
            allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
            allow_headers=["content-type"],
        )
    ],
)
asgi_app.state.repo = mcp_server.repo
