"""Motor conversacional del agente — hoy es un intérprete de comandos por patrones (regex),
NO un modelo de lenguaje. Se documenta así de explícito a propósito: esto es el punto exacto
donde Azure AI Foundry + MCPTool se conecta más adelante (ver
oraculo/docs/10-especificacion-2-agente-octo-erp.md, sección 10.9, todavía pendiente del
proyecto de ejemplo del usuario para el mecanismo de auth). Mientras eso no está desplegado,
este módulo es lo que responde en `/api/agent/chat` — deliberadamente simple y 100% testeable
sin ninguna llamada de red ni credencial, para poder demostrar el flujo completo (chat ->
acción real -> cambio real en el repositorio) sin depender de tener un modelo conectado.

Cuando Foundry esté desplegado, el reemplazo es *solo* este archivo: la ruta HTTP
(`rest_api.py`), el contrato de respuesta ({"reply", "action"}) y el frontend
(`apps/web/src/pages/AgentPage.tsx`) no cambian, porque todos hablan con las mismas
funciones de `domain/service.py` que ya usan `mcp_server.py` y `rest_api.py` — el mismo
principio de "una sola implementación de cada regla de negocio" que ya siguen esos dos.

Comandos soportados (case-insensitive, tolerante a espacios extra):
    catálogo | catalogo | productos | qué figuras hay
    stock de <SKU> | cuánto stock hay de <SKU>
    stock bajo | bajo stock | qué hay que reponer
    pedido <SKU> x<CANTIDAD> para <CLIENTE>
    ajustar <SKU> <+N|-N> [motivo]
Cualquier otra cosa devuelve un mensaje de ayuda listando estos comandos — nunca un error
silencioso ni una respuesta inventada.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .domain import service
from .domain.errors import InsufficientStockError, NotFoundError, ValidationError
from .domain.repository import ErpRepository
from .domain.types import NewOrderItemInput, StockMovementReason

_VALID_REASONS: set[StockMovementReason] = {
    "recepcion", "ajuste-manual", "venta", "merma", "produccion",
}

_HELP_TEXT = (
    "No entendí ese mensaje. Comandos que sí entiendo:\n"
    "• catálogo — lista las figuras disponibles\n"
    "• stock de <SKU> — stock actual de una variante\n"
    "• stock bajo — variantes por debajo del umbral de reposición\n"
    "• pedido <SKU> x<CANTIDAD> para <CLIENTE> — crea un pedido (descuenta stock)\n"
    "• ajustar <SKU> <+N|-N> [motivo] — ajusta stock manualmente"
)

_RE_CATALOG = re.compile(r"^(cat[aá]logo|productos|qu[eé] figuras hay)\b", re.IGNORECASE)
_RE_LOW_STOCK = re.compile(r"(stock bajo|bajo stock|qu[eé] hay que reponer|reposici[oó]n)", re.IGNORECASE)
_RE_STOCK_OF = re.compile(r"stock (?:de|del?)\s+(\S+)", re.IGNORECASE)
_RE_ORDER = re.compile(
    r"pedido\s+(\S+)\s*x\s*(\d+)\s+para\s+(.+)", re.IGNORECASE
)
_RE_ADJUST = re.compile(
    r"ajustar\s+(\S+)\s+([+-]\d+)(?:\s+(.+))?", re.IGNORECASE
)


@dataclass(slots=True)
class AgentReply:
    reply: str
    action: dict[str, Any] | None = None


def handle_message(repo: ErpRepository, message: str) -> AgentReply:
    text = message.strip()
    if not text:
        return AgentReply(reply=_HELP_TEXT)

    if _RE_CATALOG.match(text):
        return _handle_catalog(repo)

    # Los comandos estructurados (pedido/ajustar) van ANTES que las búsquedas de palabra
    # suelta (stock bajo / stock de) a propósito: "ajustar X +5 reposición de emergencia"
    # contiene la palabra "reposición", que si se buscara primero secuestraría el comando
    # de ajuste y lo confundiría con una consulta de stock bajo. Lo específico gana sobre
    # lo genérico.
    order_match = _RE_ORDER.search(text)
    if order_match:
        sku, quantity, customer = order_match.groups()
        return _handle_create_order(repo, sku=sku, quantity=int(quantity), customer=customer.strip())

    adjust_match = _RE_ADJUST.search(text)
    if adjust_match:
        sku, delta, reason_text = adjust_match.groups()
        return _handle_adjust(repo, sku=sku, delta=int(delta), reason_text=reason_text)

    if _RE_LOW_STOCK.search(text):
        return _handle_low_stock(repo)

    stock_match = _RE_STOCK_OF.search(text)
    if stock_match:
        return _handle_stock_of(repo, sku=stock_match.group(1))

    return AgentReply(reply=_HELP_TEXT)


def _handle_catalog(repo: ErpRepository) -> AgentReply:
    products = service.get_catalog_summary(repo)
    if not products:
        return AgentReply(reply="No hay figuras cargadas en el catálogo todavía.")
    lines = [
        f"• {p['name']} ({p['category']}) — {len(p['variants'])} variante(s)"
        for p in products
    ]
    return AgentReply(
        reply="Catálogo actual:\n" + "\n".join(lines),
        action={"type": "catalog_summary", "products": products},
    )


def _handle_low_stock(repo: ErpRepository) -> AgentReply:
    variants = service.list_low_stock_variants(repo)
    if not variants:
        return AgentReply(reply="Ninguna variante está por debajo de su umbral de reposición ahora mismo.")
    lines = [f"• {v.sku} ({v.name}): {v.stock_units} u., umbral {v.reorder_threshold}" for v in variants]
    return AgentReply(
        reply="Variantes por reponer:\n" + "\n".join(lines),
        action={"type": "low_stock", "variant_ids": [v.id for v in variants]},
    )


def _handle_stock_of(repo: ErpRepository, *, sku: str) -> AgentReply:
    variant = service.find_variant_by_sku(repo, sku)
    if variant is None:
        return AgentReply(reply=f"No encontré ninguna variante con el SKU '{sku}'.")
    return AgentReply(
        reply=f"{variant.sku} ({variant.name}) tiene {variant.stock_units} unidades en stock.",
        action={"type": "stock_query", "variant_id": variant.id, "stock_units": variant.stock_units},
    )


def _handle_create_order(repo: ErpRepository, *, sku: str, quantity: int, customer: str) -> AgentReply:
    variant = service.find_variant_by_sku(repo, sku)
    if variant is None:
        return AgentReply(reply=f"No encontré ninguna variante con el SKU '{sku}', no puedo crear el pedido.")
    try:
        order = service.create_order(
            repo,
            customer_name=customer,
            items=[NewOrderItemInput(variant_id=variant.id, quantity=quantity)],
        )
    except (InsufficientStockError, NotFoundError, ValidationError) as exc:
        return AgentReply(reply=f"No pude crear el pedido: {exc}")
    return AgentReply(
        reply=(
            f"Pedido {order.code} creado para {order.customer_name}: {quantity} × {sku}. "
            f"Total ${order.total_cents / 100:.2f}."
        ),
        action={"type": "order_created", "order_id": order.id, "order_code": order.code},
    )


def _handle_adjust(repo: ErpRepository, *, sku: str, delta: int, reason_text: str | None) -> AgentReply:
    variant = service.find_variant_by_sku(repo, sku)
    if variant is None:
        return AgentReply(reply=f"No encontré ninguna variante con el SKU '{sku}'.")

    reason: StockMovementReason = "ajuste-manual"
    note = reason_text.strip() if reason_text else None
    if note and note.replace("_", "-").lower() in _VALID_REASONS:
        reason = note.replace("_", "-").lower()  # type: ignore[assignment]
        note = None

    try:
        updated = service.adjust_variant_stock(
            repo, variant_id=variant.id, delta=delta, reason=reason, note=note,
        )
    except (InsufficientStockError, NotFoundError, ValidationError) as exc:
        return AgentReply(reply=f"No pude ajustar el stock: {exc}")
    signo = "+" if delta >= 0 else ""
    return AgentReply(
        reply=f"Stock de {sku} ajustado ({signo}{delta}). Nuevo stock: {updated.stock_units} u.",
        action={"type": "stock_adjusted", "variant_id": updated.id, "stock_units": updated.stock_units},
    )
