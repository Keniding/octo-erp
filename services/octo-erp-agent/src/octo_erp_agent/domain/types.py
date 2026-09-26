"""Tipos de dominio de Octo ERP — mismo shape que packages/shared/src/types.ts (TypeScript),
a propósito: si Cosmos DB pasa a ser la fuente de verdad que también lee/escribe
apps/web (ver docs/decisions/004-agente-ia-mcp-cosmosdb.md), los documentos no necesitan
traducción de modelo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

MaterialType = Literal["PLA", "PETG", "ABS", "Resina", "TPU"]

ProductCategory = Literal[
    "Anime", "Videojuegos", "Fantasia", "Miniaturas TTRPG", "Personalizado"
]

StockMovementReason = Literal[
    "recepcion", "ajuste-manual", "venta", "merma", "produccion"
]

OrderStatus = Literal[
    "borrador", "confirmado", "en_produccion", "enviado", "cancelado"
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Material:
    id: str
    name: str
    type: MaterialType
    color_hex: str
    cost_per_gram_cents: int
    stock_grams: int
    reorder_threshold_grams: int


@dataclass(slots=True)
class ProductVariant:
    id: str
    product_id: str
    name: str
    sku: str
    price_cents: int
    material_id: str
    weight_grams: int
    stock_units: int
    reorder_threshold: int


@dataclass(slots=True)
class Product:
    id: str
    name: str
    description: str
    category: ProductCategory
    created_at: str = field(default_factory=now_iso)
    image_url: str | None = None


@dataclass(slots=True)
class StockMovement:
    id: str
    target_type: Literal["variant", "material"]
    target_id: str
    delta: int
    reason: StockMovementReason
    created_at: str = field(default_factory=now_iso)
    note: str | None = None


@dataclass(slots=True)
class OrderItem:
    variant_id: str
    quantity: int
    unit_price_cents: int


@dataclass(slots=True)
class Order:
    id: str
    code: str
    customer_name: str
    items: list[OrderItem]
    total_cents: int
    status: OrderStatus = "confirmado"
    created_at: str = field(default_factory=now_iso)


@dataclass(slots=True)
class NewOrderItemInput:
    variant_id: str
    quantity: int


@dataclass(slots=True)
class NewProductVariantInput:
    name: str
    sku: str
    price_cents: int
    material_id: str
    weight_grams: int
    stock_units: int
    reorder_threshold: int
