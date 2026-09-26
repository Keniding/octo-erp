"""API REST para apps/web/apps/mobile — HTTP simple (no protocolo MCP), pensada para que un
browser le pegue directo con `fetch`. Llama a domain/service.py exactamente igual que
mcp_server.py y usa el mismo repositorio (ver http_app.py) — no hay una segunda copia de la
regla "nunca vender más stock del disponible".

Reemplaza a `packages/shared/src/store.ts` como fuente de verdad para apps/web una vez que
esa app la consuma (ver docs/decisions/005-cache-frontend-vs-fuente-de-verdad.md); hasta que
eso pase, esta API y el store en memoria del frontend coexisten sin tocarse.

Los documentos de respuesta reusan los mismos serializadores camelCase que
repositories/cosmos.py (_product_to_doc, etc.) porque son exactamente el shape de
packages/shared/src/types.ts — un solo lugar que traduce snake_case (Python) a camelCase
(TS/JSON), no dos.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import agent_chat
from .domain import service
from .domain.errors import InsufficientStockError, NotFoundError, ValidationError
from .domain.repository import ErpRepository
from .domain.types import NewOrderItemInput, NewProductVariantInput
from .repositories.cosmos import (
    _material_to_doc,
    _movement_to_doc,
    _order_to_doc,
    _product_to_doc,
    _variant_to_doc,
)


def _error_response(exc: Exception) -> JSONResponse:
    if isinstance(exc, ValidationError):
        return JSONResponse({"error": str(exc)}, status_code=400)
    if isinstance(exc, NotFoundError):
        return JSONResponse({"error": str(exc)}, status_code=404)
    if isinstance(exc, InsufficientStockError):
        return JSONResponse({"error": str(exc)}, status_code=409)
    raise exc


async def get_state(request: Request) -> JSONResponse:
    """Bootstrap para el frontend: mismo shape inicial que useErpStore en
    packages/shared/src/store.ts (products, variants, materials, orders — `movements` vacío,
    igual que el store en memoria, que tampoco lo pre-carga)."""
    repo: ErpRepository = request.app.state.repo
    return JSONResponse(
        {
            "products": [_product_to_doc(p) for p in repo.list_products()],
            "variants": [_variant_to_doc(v) for v in repo.list_variants()],
            "materials": [_material_to_doc(m) for m in repo.list_materials()],
            "orders": [_order_to_doc(o) for o in repo.list_orders()],
            "movements": [],
        }
    )


async def create_product(request: Request) -> JSONResponse:
    repo: ErpRepository = request.app.state.repo
    body = await request.json()
    try:
        product = service.add_product(
            repo,
            name=body.get("name", ""),
            description=body.get("description", ""),
            category=body["category"],
            image_url=body.get("imageUrl"),
            variants=[
                NewProductVariantInput(
                    name=v["name"], sku=v["sku"], price_cents=v["priceCents"],
                    material_id=v["materialId"], weight_grams=v["weightGrams"],
                    stock_units=v["stockUnits"], reorder_threshold=v["reorderThreshold"],
                )
                for v in body.get("variants", [])
            ],
        )
    except (ValidationError, NotFoundError, InsufficientStockError) as exc:
        return _error_response(exc)
    variants = repo.list_variants(product.id)
    return JSONResponse(
        {"product": _product_to_doc(product), "variants": [_variant_to_doc(v) for v in variants]},
        status_code=201,
    )


async def adjust_variant_stock(request: Request) -> JSONResponse:
    repo: ErpRepository = request.app.state.repo
    body = await request.json()
    try:
        variant = service.adjust_variant_stock(
            repo, variant_id=request.path_params["variant_id"], delta=body["delta"],
            reason=body["reason"], note=body.get("note"),
        )
    except (ValidationError, NotFoundError, InsufficientStockError) as exc:
        return _error_response(exc)
    return JSONResponse(_variant_to_doc(variant))


async def adjust_material_stock(request: Request) -> JSONResponse:
    repo: ErpRepository = request.app.state.repo
    body = await request.json()
    try:
        material = service.adjust_material_stock(
            repo, material_id=request.path_params["material_id"], delta=body["delta"],
            reason=body["reason"], note=body.get("note"),
        )
    except (ValidationError, NotFoundError, InsufficientStockError) as exc:
        return _error_response(exc)
    return JSONResponse(_material_to_doc(material))


async def create_order(request: Request) -> JSONResponse:
    repo: ErpRepository = request.app.state.repo
    body = await request.json()
    try:
        order = service.create_order(
            repo,
            customer_name=body.get("customerName", ""),
            items=[
                NewOrderItemInput(variant_id=i["variantId"], quantity=i["quantity"])
                for i in body.get("items", [])
            ],
        )
    except (ValidationError, NotFoundError, InsufficientStockError) as exc:
        return _error_response(exc)
    return JSONResponse(_order_to_doc(order), status_code=201)


async def update_order_status(request: Request) -> JSONResponse:
    # Sin validación de negocio — igual que updateOrderStatus en
    # packages/shared/src/store.ts, una mutación directa sin reglas asociadas.
    repo: ErpRepository = request.app.state.repo
    order_id = request.path_params["order_id"]
    order = repo.get_order(order_id)
    if order is None:
        return _error_response(NotFoundError("Pedido", order_id))
    body = await request.json()
    order.status = body["status"]
    repo.save_order(order)
    return JSONResponse(_order_to_doc(order))


async def agent_chat_endpoint(request: Request) -> JSONResponse:
    """Ver agent_chat.py — hoy es un intérprete de comandos, no un LLM (documentado ahí en
    detalle). Actúa sobre `request.app.state.repo`, el mismo repositorio que /api/* y /mcp,
    así que sus acciones son visibles de inmediato para cualquier otro cliente que lea de
    ahí (incluido el próximo poll de apps/web)."""
    repo: ErpRepository = request.app.state.repo
    body = await request.json()
    message = body.get("message", "")
    if not isinstance(message, str):
        return JSONResponse({"error": "'message' debe ser un string."}, status_code=400)
    result = await agent_chat.handle_message(repo, message)
    return JSONResponse({"reply": result.reply, "action": result.action})


async def list_movements(request: Request) -> JSONResponse:
    repo: ErpRepository = request.app.state.repo
    target_id = request.query_params.get("targetId")
    if not target_id:
        return JSONResponse({"error": "Falta el query param targetId."}, status_code=400)
    movements = repo.list_movements(target_id)
    return JSONResponse([_movement_to_doc(m) for m in movements])


api_routes = [
    Route("/api/state", get_state, methods=["GET"]),
    Route("/api/products", create_product, methods=["POST"]),
    Route("/api/variants/{variant_id}/stock-adjustments", adjust_variant_stock, methods=["POST"]),
    Route("/api/materials/{material_id}/stock-adjustments", adjust_material_stock, methods=["POST"]),
    Route("/api/orders", create_order, methods=["POST"]),
    Route("/api/orders/{order_id}/status", update_order_status, methods=["PATCH"]),
    Route("/api/movements", list_movements, methods=["GET"]),
    Route("/api/agent/chat", agent_chat_endpoint, methods=["POST"]),
]
