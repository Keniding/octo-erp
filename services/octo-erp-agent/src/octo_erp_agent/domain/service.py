"""Reglas de negocio de Octo ERP — puerto 1:1 de packages/shared/src/store.ts.
Depende solo de ErpRepository (inyectado), nunca de una implementación concreta: estas
funciones son las que llaman tanto el servidor MCP custom (octo_erp_agent/mcp_server.py)
como, eventualmente, una API REST para apps/web/apps/mobile — un solo lugar con la regla
de "nunca vender más stock del disponible", no duplicada en dos stacks.
"""

from __future__ import annotations

import random
import string
from datetime import datetime, timezone

from .errors import InsufficientStockError, NotFoundError, ValidationError
from .repository import ErpRepository
from .types import (
    Material,
    NewOrderItemInput,
    NewProductVariantInput,
    Order,
    OrderItem,
    Product,
    ProductCategory,
    ProductVariant,
    StockMovement,
    StockMovementReason,
)


def make_id(prefix: str) -> str:
    """Mismo esquema que packages/shared/src/id.ts: prefijo + timestamp base36 + random.
    No es un UUID a propósito — legible en logs/demos, igual que en el TS original."""
    ts = format(int(datetime.now(timezone.utc).timestamp() * 1000), "x")
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=7))
    return f"{prefix}-{ts}-{rand}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_product(
    repo: ErpRepository,
    *,
    name: str,
    description: str,
    category: ProductCategory,
    variants: list[NewProductVariantInput],
    image_url: str | None = None,
) -> Product:
    if not name.strip():
        raise ValidationError("El nombre de la figura es obligatorio.")
    if not variants:
        raise ValidationError("Agregá al menos una variante.")

    product = Product(
        id=make_id("prod"),
        name=name.strip(),
        description=description.strip(),
        category=category,
        image_url=image_url,
    )
    repo.save_product(product)

    for v in variants:
        repo.save_variant(
            ProductVariant(
                id=make_id("var"),
                product_id=product.id,
                name=v.name,
                sku=v.sku,
                price_cents=v.price_cents,
                material_id=v.material_id,
                weight_grams=v.weight_grams,
                stock_units=v.stock_units,
                reorder_threshold=v.reorder_threshold,
            )
        )
    return product


def adjust_variant_stock(
    repo: ErpRepository,
    *,
    variant_id: str,
    delta: int,
    reason: StockMovementReason,
    note: str | None = None,
) -> ProductVariant:
    variant = repo.get_variant(variant_id)
    if variant is None:
        raise NotFoundError("Variante", variant_id)

    next_stock = variant.stock_units + delta
    if next_stock < 0:
        raise InsufficientStockError(variant_id, variant.stock_units, -delta)

    repo.set_variant_stock(variant_id, next_stock)
    repo.add_movement(
        StockMovement(
            id=make_id("mov"),
            target_type="variant",
            target_id=variant_id,
            delta=delta,
            reason=reason,
            note=note,
        )
    )
    variant.stock_units = next_stock
    return variant


def adjust_material_stock(
    repo: ErpRepository,
    *,
    material_id: str,
    delta: int,
    reason: StockMovementReason,
    note: str | None = None,
) -> Material:
    material = repo.get_material(material_id)
    if material is None:
        raise NotFoundError("Material", material_id)

    next_stock = material.stock_grams + delta
    if next_stock < 0:
        raise InsufficientStockError(material_id, material.stock_grams, -delta)

    repo.set_material_stock(material_id, next_stock)
    repo.add_movement(
        StockMovement(
            id=make_id("mov"),
            target_type="material",
            target_id=material_id,
            delta=delta,
            reason=reason,
            note=note,
        )
    )
    material.stock_grams = next_stock
    return material


def create_order(
    repo: ErpRepository,
    *,
    customer_name: str,
    items: list[NewOrderItemInput],
) -> Order:
    if not customer_name.strip():
        raise ValidationError("El nombre del cliente es obligatorio.")
    if not items:
        raise ValidationError("El pedido necesita al menos un artículo.")

    # Pre-chequeo de TODOS los items antes de mutar nada — igual que
    # packages/shared/src/store.ts: un pedido no puede quedar "a medias" confirmado.
    resolved: list[tuple[ProductVariant, int]] = []
    for item in items:
        variant = repo.get_variant(item.variant_id)
        if variant is None:
            raise NotFoundError("Variante", item.variant_id)
        if variant.stock_units < item.quantity:
            raise InsufficientStockError(item.variant_id, variant.stock_units, item.quantity)
        resolved.append((variant, item.quantity))

    order_items = [
        OrderItem(variant_id=v.id, quantity=qty, unit_price_cents=v.price_cents)
        for v, qty in resolved
    ]
    total_cents = sum(i.unit_price_cents * i.quantity for i in order_items)

    order = Order(
        id=make_id("ord"),
        code=f"ORD-{1000 + repo.count_orders() + 1}",
        customer_name=customer_name.strip(),
        items=order_items,
        total_cents=total_cents,
        status="confirmado",
    )
    repo.save_order(order)

    for variant, qty in resolved:
        repo.set_variant_stock(variant.id, variant.stock_units - qty)
        repo.add_movement(
            StockMovement(
                id=make_id("mov"),
                target_type="variant",
                target_id=variant.id,
                delta=-qty,
                reason="venta",
                note=order.code,
            )
        )

    return order


def find_variant_by_sku(repo: ErpRepository, sku: str) -> ProductVariant | None:
    """Búsqueda por SKU (no por id) — la unidad con la que la gente habla de una variante en
    lenguaje natural ('el SAM-10-RAW') es el SKU, nunca el id interno generado por
    make_id(). Usado por agent_chat.py; no tiene equivalente directo en
    packages/shared/src/store.ts porque la UI de apps/web siempre trabaja con ids desde los
    <select>, nunca pide al usuario que escriba un SKU a mano."""
    needle = sku.strip().lower()
    for variant in repo.list_variants():
        if variant.sku.lower() == needle:
            return variant
    return None


def list_low_stock_variants(repo: ErpRepository) -> list[ProductVariant]:
    return [v for v in repo.list_variants() if v.stock_units <= v.reorder_threshold]


def list_low_stock_materials(repo: ErpRepository) -> list[Material]:
    return [m for m in repo.list_materials() if m.stock_grams <= m.reorder_threshold_grams]


def get_catalog_summary(
    repo: ErpRepository, *, category: ProductCategory | None = None
) -> list[dict]:
    products = repo.list_products()
    if category is not None:
        products = [p for p in products if p.category == category]

    summary = []
    for product in products:
        variants = repo.list_variants(product.id)
        summary.append(
            {
                "id": product.id,
                "name": product.name,
                "category": product.category,
                "variants": [
                    {
                        "id": v.id,
                        "name": v.name,
                        "sku": v.sku,
                        "price_cents": v.price_cents,
                        "stock_units": v.stock_units,
                    }
                    for v in variants
                ],
            }
        )
    return summary
