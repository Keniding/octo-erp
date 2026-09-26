"""Tests reales de las reglas de negocio (domain/service.py) contra InMemoryRepository.
Sin red, sin Azure, deterministas — corren con `uv run pytest`. Espejo de los casos ya
cubiertos en apps/web/e2e/flows.spec.ts (TypeScript) para las mismas reglas."""

from __future__ import annotations

import pytest

from octo_erp_agent.domain import service
from octo_erp_agent.domain.errors import InsufficientStockError, NotFoundError, ValidationError
from octo_erp_agent.domain.types import NewOrderItemInput, NewProductVariantInput
from octo_erp_agent.repositories.in_memory import InMemoryRepository


@pytest.fixture
def repo() -> InMemoryRepository:
    return InMemoryRepository()


# -- add_product -------------------------------------------------------------------------

def test_add_product_creates_product_and_variants(repo: InMemoryRepository):
    product = service.add_product(
        repo,
        name="Golem de raíz",
        description="Golem tallado con motivos botánicos.",
        category="Fantasia",
        variants=[
            NewProductVariantInput(
                name="15cm — sin pintar", sku="GOL-15-RAW", price_cents=3250,
                material_id="mat-pla-negro", weight_grams=140, stock_units=6,
                reorder_threshold=3,
            )
        ],
    )
    assert product.name == "Golem de raíz"
    variants = repo.list_variants(product.id)
    assert len(variants) == 1
    assert variants[0].sku == "GOL-15-RAW"
    assert variants[0].stock_units == 6


def test_add_product_requires_name(repo: InMemoryRepository):
    with pytest.raises(ValidationError):
        service.add_product(
            repo, name="   ", description="", category="Fantasia",
            variants=[NewProductVariantInput(
                name="x", sku="x", price_cents=100, material_id="mat-pla-negro",
                weight_grams=1, stock_units=0, reorder_threshold=0,
            )],
        )


def test_add_product_requires_at_least_one_variant(repo: InMemoryRepository):
    with pytest.raises(ValidationError):
        service.add_product(
            repo, name="Figura", description="", category="Fantasia", variants=[],
        )


# -- adjust_variant_stock -----------------------------------------------------------------

def test_adjust_variant_stock_increases_stock(repo: InMemoryRepository):
    variant = service.adjust_variant_stock(
        repo, variant_id="var-samurai-10-sin-pintar", delta=5, reason="recepcion",
    )
    assert variant.stock_units == 19  # seed: 14 + 5
    assert repo.get_variant("var-samurai-10-sin-pintar").stock_units == 19


def test_adjust_variant_stock_rejects_negative_result(repo: InMemoryRepository):
    # seed var-dragon-resina tiene stock 2
    with pytest.raises(InsufficientStockError) as exc_info:
        service.adjust_variant_stock(
            repo, variant_id="var-dragon-resina", delta=-10, reason="merma",
        )
    assert exc_info.value.available == 2
    assert exc_info.value.requested == 10
    # el stock NO debe haber cambiado
    assert repo.get_variant("var-dragon-resina").stock_units == 2


def test_adjust_variant_stock_unknown_variant_raises_not_found(repo: InMemoryRepository):
    with pytest.raises(NotFoundError):
        service.adjust_variant_stock(
            repo, variant_id="var-no-existe", delta=1, reason="recepcion",
        )


def test_adjust_variant_stock_records_movement(repo: InMemoryRepository):
    service.adjust_variant_stock(
        repo, variant_id="var-samurai-10-sin-pintar", delta=3, reason="recepcion",
        note="Reposición de taller",
    )
    movements = repo.list_movements("var-samurai-10-sin-pintar")
    assert len(movements) == 1
    assert movements[0].delta == 3
    assert movements[0].reason == "recepcion"
    assert movements[0].note == "Reposición de taller"


# -- create_order -------------------------------------------------------------------------

def test_create_order_deducts_stock_and_computes_total(repo: InMemoryRepository):
    order = service.create_order(
        repo, customer_name="Taller Origami",
        items=[NewOrderItemInput(variant_id="var-samurai-10-sin-pintar", quantity=2)],
    )
    assert order.customer_name == "Taller Origami"
    assert order.total_cents == 2 * 1800  # price_cents del seed
    assert order.status == "confirmado"
    assert repo.get_variant("var-samurai-10-sin-pintar").stock_units == 12  # 14 - 2


def test_create_order_generates_sequential_code(repo: InMemoryRepository):
    # seed ya trae 1 pedido (ORD-1001) -> el siguiente debe ser ORD-1002
    order = service.create_order(
        repo, customer_name="Cliente Nuevo",
        items=[NewOrderItemInput(variant_id="var-mecha-standard", quantity=1)],
    )
    assert order.code == "ORD-1002"


def test_create_order_records_venta_movement_per_item(repo: InMemoryRepository):
    service.create_order(
        repo, customer_name="Taller Origami",
        items=[NewOrderItemInput(variant_id="var-samurai-10-sin-pintar", quantity=2)],
    )
    movements = repo.list_movements("var-samurai-10-sin-pintar")
    assert len(movements) == 1
    assert movements[0].delta == -2
    assert movements[0].reason == "venta"


def test_create_order_rejects_insufficient_stock_without_mutating_anything(repo: InMemoryRepository):
    # var-dragon-resina tiene stock 2 en el seed
    orders_before = repo.count_orders()
    with pytest.raises(InsufficientStockError):
        service.create_order(
            repo, customer_name="Cliente sin stock",
            items=[NewOrderItemInput(variant_id="var-dragon-resina", quantity=99)],
        )
    assert repo.count_orders() == orders_before
    assert repo.get_variant("var-dragon-resina").stock_units == 2


def test_create_order_multi_item_all_or_nothing(repo: InMemoryRepository):
    """Si UNA línea del pedido no tiene stock, NINGUNA línea se descuenta — ni siquiera
    la que sí tenía stock suficiente. Mismo comportamiento que packages/shared/src/store.ts
    (pre-chequeo de todos los items antes de mutar)."""
    stock_before = repo.get_variant("var-samurai-10-sin-pintar").stock_units
    with pytest.raises(InsufficientStockError):
        service.create_order(
            repo, customer_name="Pedido mixto",
            items=[
                NewOrderItemInput(variant_id="var-samurai-10-sin-pintar", quantity=1),  # sí hay stock
                NewOrderItemInput(variant_id="var-dragon-resina", quantity=99),  # no hay stock
            ],
        )
    assert repo.get_variant("var-samurai-10-sin-pintar").stock_units == stock_before


def test_create_order_requires_customer_name(repo: InMemoryRepository):
    with pytest.raises(ValidationError):
        service.create_order(
            repo, customer_name="  ",
            items=[NewOrderItemInput(variant_id="var-samurai-10-sin-pintar", quantity=1)],
        )


def test_create_order_requires_at_least_one_item(repo: InMemoryRepository):
    with pytest.raises(ValidationError):
        service.create_order(repo, customer_name="Cliente", items=[])


# -- low stock queries ----------------------------------------------------------------------

def test_list_low_stock_variants_matches_seed_thresholds(repo: InMemoryRepository):
    low = {v.id for v in service.list_low_stock_variants(repo)}
    # seed: samurai-18 (4 <= 3? NO, 4 > 3 -> no está), mecha (7 <= 4? no), dragon (2 <= 6? sí)
    assert "var-dragon-resina" in low
    assert "var-samurai-10-sin-pintar" not in low  # 14 stock, umbral 5


def test_list_low_stock_materials_empty_on_fresh_seed(repo: InMemoryRepository):
    # los 4 materiales semilla están todos por ENCIMA de su umbral (ver seed.py) —
    # ninguno debería aparecer como bajo stock todavía.
    assert service.list_low_stock_materials(repo) == []


def test_list_low_stock_materials_detects_after_consumption(repo: InMemoryRepository):
    # mat-resina-gris: stock 350, umbral 300 (seed) -> consumir 60g lo deja en 290, bajo umbral
    service.adjust_material_stock(
        repo, material_id="mat-resina-gris", delta=-60, reason="produccion",
    )
    low = {m.id for m in service.list_low_stock_materials(repo)}
    assert "mat-resina-gris" in low
