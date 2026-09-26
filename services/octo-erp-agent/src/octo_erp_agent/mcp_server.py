"""Servidor MCP custom de Octo ERP — mismo patrón exacto que oraculo/mcp_server.py
(ver ese archivo y oraculo/docs/04-protocolo-mcp.md): tools con nombre y validación de
negocio, nunca SQL/queries crudas expuestas al agente. Complementa al MCP nativo
(AzureCosmosDB/MCPToolKit, ver oraculo/docs/10-especificacion-2-agente-octo-erp.md, 10.3)
que sí puede explorar/consultar Cosmos DB de forma genérica.

Selección de repositorio: si COSMOS_ENDPOINT está seteado, usa CosmosRepository (la fuente
de verdad real en producción). Si no, cae a InMemoryRepository — para desarrollo local y
para los tests de este mismo repo (tests/test_mcp_server.py), sin depender de una cuenta de
Azure real.

Uso local:
    uv run python -m octo_erp_agent.mcp_server
Corre en http://0.0.0.0:8000/mcp por defecto (mismas env vars MCP_SERVER_HOST/PORT que
oraculo/mcp_server.py).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from .domain import service
from .domain.errors import InsufficientStockError, NotFoundError, ValidationError
from .domain.repository import ErpRepository
from .domain.types import NewOrderItemInput, NewProductVariantInput

load_dotenv()


def _build_repository() -> ErpRepository:
    endpoint = os.environ.get("COSMOS_ENDPOINT")
    if endpoint:
        from .repositories.cosmos import CosmosRepository

        return CosmosRepository(endpoint=endpoint)

    from .repositories.in_memory import InMemoryRepository

    return InMemoryRepository()


repo: ErpRepository = _build_repository()

mcp = MCPServer(
    "octo-erp-tools",
    instructions=(
        "Herramientas de Octo ERP: catálogo, inventario y pedidos de figuras impresas en "
        "3D. Antes de confirmar un pedido, siempre verificá stock disponible con "
        "get_variant_stock — nunca asumas disponibilidad."
    ),
)


@mcp.tool()
def get_catalog_summary(category: str | None = None) -> dict:
    """Devuelve el catálogo de figuras (producto + sus variantes con precio y stock).
    Si se pasa `category`, filtra por esa categoría exacta (ej. 'Fantasia', 'Anime')."""
    return {"products": service.get_catalog_summary(repo, category=category)}


@mcp.tool()
def get_variant_stock(variant_id: str) -> dict:
    """Consulta el stock disponible ahora mismo de una variante específica por su id."""
    variant = repo.get_variant(variant_id)
    if variant is None:
        return {"error": f"Variante no encontrada: {variant_id}"}
    return {
        "variant_id": variant.id,
        "name": variant.name,
        "sku": variant.sku,
        "stock_units": variant.stock_units,
        "reorder_threshold": variant.reorder_threshold,
    }


@mcp.tool()
def list_low_stock_variants() -> dict:
    """Lista las variantes de producto cuyo stock está en o por debajo del umbral de
    reposición — útil para responder '¿qué figuras hay que reponer?'."""
    variants = service.list_low_stock_variants(repo)
    return {
        "variants": [
            {"variant_id": v.id, "name": v.name, "sku": v.sku, "stock_units": v.stock_units,
             "reorder_threshold": v.reorder_threshold}
            for v in variants
        ]
    }


@mcp.tool()
def list_low_stock_materials() -> dict:
    """Lista los materiales (filamento/resina) cuyo stock en gramos está en o por debajo
    del umbral de reposición."""
    materials = service.list_low_stock_materials(repo)
    return {
        "materials": [
            {"material_id": m.id, "name": m.name, "stock_grams": m.stock_grams,
             "reorder_threshold_grams": m.reorder_threshold_grams}
            for m in materials
        ]
    }


@mcp.tool()
def create_order(customer_name: str, items: list[dict]) -> dict:
    """Crea un pedido y descuenta el stock correspondiente. `items` es una lista de
    {"variant_id": str, "quantity": int}. Valida stock suficiente para CADA línea antes de
    confirmar nada — si alguna línea no tiene stock, no se crea el pedido y se devuelve
    un error explicando cuál."""
    try:
        order = service.create_order(
            repo,
            customer_name=customer_name,
            items=[NewOrderItemInput(variant_id=i["variant_id"], quantity=i["quantity"]) for i in items],
        )
    except (InsufficientStockError, NotFoundError, ValidationError) as exc:
        return {"error": str(exc)}
    return {
        "order_id": order.id,
        "code": order.code,
        "status": order.status,
        "total_cents": order.total_cents,
    }


@mcp.tool()
def adjust_variant_stock(variant_id: str, delta: int, reason: str, note: str | None = None) -> dict:
    """Ajusta manualmente el stock de una variante (ej. recepción de mercadería, merma).
    `delta` positivo suma stock, negativo lo resta. `reason` debe ser uno de: recepcion,
    ajuste-manual, venta, merma, produccion."""
    try:
        variant = service.adjust_variant_stock(
            repo, variant_id=variant_id, delta=delta, reason=reason, note=note,  # type: ignore[arg-type]
        )
    except (InsufficientStockError, NotFoundError, ValidationError) as exc:
        return {"error": str(exc)}
    return {"variant_id": variant.id, "new_stock_units": variant.stock_units}


def _reject_get(app):
    """Idéntico a oraculo/mcp_server.py — el transporte streamable-http abre un stream SSE
    de larga duración en cada GET; en Azure Functions (serverless) eso se queda colgado
    hasta que la plataforma mata la ejecución por timeout. Este servidor solo usa
    request/response (POST), así que responde 405 de inmediato a cualquier GET."""

    async def wrapped(scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "GET":
            await send(
                {
                    "type": "http.response.start",
                    "status": 405,
                    "headers": [(b"content-type", b"text/plain"), (b"allow", b"POST, DELETE")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"Method Not Allowed: este servidor MCP no soporta push del "
                    b"servidor (SSE via GET), solo request/response via POST.",
                }
            )
            return
        await app(scope, receive, send)

    return wrapped


# A diferencia de oraculo/mcp_server.py (100% lectura pública), este servidor SI puede
# modificar datos de negocio (create_order, adjust_variant_stock) — la protección real no
# vive acá sino en la capa de hosting (Azure Functions: Easy Auth/Entra ID o function key,
# ver oraculo/docs/10-especificacion-2-agente-octo-erp.md, sección 10.9). Mantener
# `enable_dns_rebinding_protection=False` sigue siendo correcto: la razón de oraculo (el
# Host header en Azure Functions no es controlable por el cliente) aplica igual acá — la
# protección de acceso es responsabilidad de la capa de auth, no de esta opción del SDK MCP.
_transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)

asgi_app = _reject_get(
    mcp.streamable_http_app(stateless_http=True, transport_security=_transport_security)
)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_SERVER_PORT", "8000"))
    uvicorn.run(asgi_app, host=host, port=port)
