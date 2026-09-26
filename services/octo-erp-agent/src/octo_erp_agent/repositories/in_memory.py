"""Repositorio en memoria — SOLO para tests y para correr el servidor MCP localmente sin
Azure. Nunca es la fuente de verdad en producción (ver
docs/decisions/004-agente-ia-mcp-cosmosdb.md): en producción, CosmosRepository es la única
fuente de verdad real. Implementa el mismo Protocol (ErpRepository) que CosmosRepository,
así el service.py y las tools MCP no saben ni les importa cuál de las dos están usando.
"""

from __future__ import annotations

import copy

from ..domain.types import Material, Order, Product, ProductVariant, StockMovement
from .seed import SEED_MATERIALS, SEED_ORDERS, SEED_PRODUCTS, SEED_VARIANTS


class InMemoryRepository:
    def __init__(self, *, seeded: bool = True) -> None:
        self._products: dict[str, Product] = {}
        self._variants: dict[str, ProductVariant] = {}
        self._materials: dict[str, Material] = {}
        self._orders: dict[str, Order] = {}
        self._movements: list[StockMovement] = []
        if seeded:
            for p in SEED_PRODUCTS:
                self._products[p.id] = copy.deepcopy(p)
            for v in SEED_VARIANTS:
                self._variants[v.id] = copy.deepcopy(v)
            for m in SEED_MATERIALS:
                self._materials[m.id] = copy.deepcopy(m)
            for o in SEED_ORDERS:
                self._orders[o.id] = copy.deepcopy(o)

    # -- products --
    def list_products(self) -> list[Product]:
        return list(self._products.values())

    def get_product(self, product_id: str) -> Product | None:
        return self._products.get(product_id)

    def save_product(self, product: Product) -> None:
        self._products[product.id] = product

    # -- variants --
    def list_variants(self, product_id: str | None = None) -> list[ProductVariant]:
        values = list(self._variants.values())
        if product_id is not None:
            values = [v for v in values if v.product_id == product_id]
        return values

    def get_variant(self, variant_id: str) -> ProductVariant | None:
        variant = self._variants.get(variant_id)
        return copy.deepcopy(variant) if variant else None

    def save_variant(self, variant: ProductVariant) -> None:
        self._variants[variant.id] = variant

    def set_variant_stock(self, variant_id: str, new_stock: int) -> None:
        if variant_id not in self._variants:
            raise KeyError(variant_id)
        self._variants[variant_id].stock_units = new_stock

    # -- materials --
    def list_materials(self) -> list[Material]:
        return list(self._materials.values())

    def get_material(self, material_id: str) -> Material | None:
        material = self._materials.get(material_id)
        return copy.deepcopy(material) if material else None

    def set_material_stock(self, material_id: str, new_stock: int) -> None:
        if material_id not in self._materials:
            raise KeyError(material_id)
        self._materials[material_id].stock_grams = new_stock

    # -- orders --
    def list_orders(self) -> list[Order]:
        return list(self._orders.values())

    def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def save_order(self, order: Order) -> None:
        self._orders[order.id] = order

    def count_orders(self) -> int:
        return len(self._orders)

    # -- movements --
    def add_movement(self, movement: StockMovement) -> None:
        self._movements.append(movement)

    def list_movements(self, target_id: str) -> list[StockMovement]:
        return [m for m in self._movements if m.target_id == target_id]
