"""Mismos datos semilla, mismos IDs, que packages/shared/src/seed.ts — a propósito, para
que una demo cruzada (web en TS + agente en Python) hable de las mismas figuras."""

from __future__ import annotations

from ..domain.types import Material, Order, OrderItem, Product, ProductVariant

SEED_MATERIALS: list[Material] = [
    Material(
        id="mat-pla-negro", name="PLA Negro", type="PLA", color_hex="#191919",
        cost_per_gram_cents=4, stock_grams=4200, reorder_threshold_grams=500,
    ),
    Material(
        id="mat-pla-terracota", name="PLA Terracota", type="PLA", color_hex="#cc5a3f",
        cost_per_gram_cents=5, stock_grams=1800, reorder_threshold_grams=500,
    ),
    Material(
        id="mat-petg-transparente", name="PETG Transparente", type="PETG",
        color_hex="#bdd2cb", cost_per_gram_cents=6, stock_grams=900,
        reorder_threshold_grams=400,
    ),
    Material(
        id="mat-resina-gris", name="Resina Gris Detalle", type="Resina",
        color_hex="#7d8d78", cost_per_gram_cents=12, stock_grams=350,
        reorder_threshold_grams=300,
    ),
]

SEED_PRODUCTS: list[Product] = [
    Product(
        id="prod-samurai", name="Samurai errante",
        description="Figura de samurái en pose de combate.",
        category="Fantasia", created_at="2026-01-12T10:00:00.000Z",
    ),
    Product(
        id="prod-mecha", name="Centinela Mecha MK-II",
        description="Mecha articulado de línea limpia.",
        category="Videojuegos", created_at="2026-02-03T10:00:00.000Z",
    ),
    Product(
        id="prod-dragon-whelp", name="Dragoncillo de cuarzo",
        description="Miniatura de dragón joven para mesa de rol.",
        category="Miniaturas TTRPG", created_at="2026-02-20T10:00:00.000Z",
    ),
]

SEED_VARIANTS: list[ProductVariant] = [
    ProductVariant(
        id="var-samurai-10-sin-pintar", product_id="prod-samurai",
        name="10cm — sin pintar", sku="SAM-10-RAW", price_cents=1800,
        material_id="mat-pla-negro", weight_grams=85, stock_units=14,
        reorder_threshold=5,
    ),
    ProductVariant(
        id="var-samurai-18-pintada", product_id="prod-samurai",
        name="18cm — pintada", sku="SAM-18-PAINT", price_cents=5200,
        material_id="mat-pla-terracota", weight_grams=210, stock_units=4,
        reorder_threshold=3,
    ),
    ProductVariant(
        id="var-mecha-standard", product_id="prod-mecha",
        name="Estándar — articulado", sku="MEC-STD", price_cents=4600,
        material_id="mat-petg-transparente", weight_grams=260, stock_units=7,
        reorder_threshold=4,
    ),
    ProductVariant(
        id="var-dragon-resina", product_id="prod-dragon-whelp",
        name="Base 25mm — resina", sku="DRG-25-RES", price_cents=2400,
        material_id="mat-resina-gris", weight_grams=22, stock_units=2,
        reorder_threshold=6,
    ),
]

SEED_ORDERS: list[Order] = [
    Order(
        id="ord-1001", code="ORD-1001", customer_name="Estudio Katana",
        items=[OrderItem(variant_id="var-samurai-10-sin-pintar", quantity=2, unit_price_cents=1800)],
        total_cents=3600, status="confirmado", created_at="2026-03-01T15:30:00.000Z",
    ),
]
