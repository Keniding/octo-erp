"""Round-trip real contra una cuenta de Azure Cosmos DB real — no un mock, no el emulador.

Se salta automáticamente si no hay `COSMOS_ENDPOINT` en el entorno (por ejemplo, en un
checkout local sin `az login` o sin la infraestructura de `infra/main.bicep` desplegada).
Corre en CI en el job de integración (ver `.github/workflows/octo-erp-agent-ci.yml`), que se
autentica contra Azure vía OIDC antes de esta prueba — nunca con una connection string ni una
key (la cuenta tiene `disableLocalAuth: true`, ver infra/main.bicep).

Usa IDs con prefijo `test-` y limpia lo que crea al final, para poder correr repetidas veces
contra la misma cuenta compartida de dev sin acumular basura.
"""

from __future__ import annotations

import os
import uuid

import pytest

from octo_erp_agent.domain.types import Material, Order, OrderItem, Product, ProductVariant, StockMovement
from octo_erp_agent.repositories.cosmos import CosmosRepository, _material_to_doc

COSMOS_ENDPOINT = os.environ.get("COSMOS_ENDPOINT")

pytestmark = pytest.mark.skipif(
    not COSMOS_ENDPOINT,
    reason="COSMOS_ENDPOINT no está seteado — sin cuenta de Cosmos DB real para probar contra.",
)


@pytest.fixture(scope="module")
def repo() -> CosmosRepository:
    return CosmosRepository(endpoint=COSMOS_ENDPOINT)


def _unique_id(prefix: str) -> str:
    return f"test-{prefix}-{uuid.uuid4().hex[:8]}"


def test_product_round_trip(repo: CosmosRepository):
    product_id = _unique_id("product")
    product = Product(
        id=product_id, name="Figura de prueba de integración", description="temporal",
        category="Test", created_at="2026-09-26T00:00:00.000Z",
    )
    repo.save_product(product)
    try:
        fetched = repo.get_product(product_id)
        assert fetched is not None
        assert fetched.name == "Figura de prueba de integración"
        assert repo.get_product(_unique_id("nonexistent")) is None
    finally:
        repo._products.delete_item(item=product_id, partition_key=product_id)


def test_variant_stock_round_trip_against_real_account(repo: CosmosRepository):
    product_id = _unique_id("product")
    variant_id = _unique_id("variant")
    variant = ProductVariant(
        id=variant_id, product_id=product_id, name="Variante de prueba", sku="TEST-SKU",
        price_cents=1000, material_id="mat-test", weight_grams=50, stock_units=10,
        reorder_threshold=2,
    )
    repo.save_variant(variant)
    try:
        assert repo.get_variant(variant_id).stock_units == 10

        repo.set_variant_stock(variant_id, 7)
        assert repo.get_variant(variant_id).stock_units == 7

        assert [v.id for v in repo.list_variants(product_id=product_id)] == [variant_id]
    finally:
        repo._variants.delete_item(item=variant_id, partition_key=product_id)


def test_material_stock_round_trip_against_real_account(repo: CosmosRepository):
    material_id = _unique_id("material")
    material = Material(
        id=material_id, name="Filamento de prueba", type="PLA", color_hex="#000000",
        cost_per_gram_cents=5, stock_grams=100, reorder_threshold_grams=20,
    )
    # No hay save_material en el Protocol (ver domain/repository.py) — la creación inicial
    # de un material es un caso de seed/admin fuera del alcance del agente conversacional,
    # así que se escribe el documento directo al container, igual que haría un seed script.
    repo._materials.upsert_item(_material_to_doc(material))
    try:
        assert repo.get_material(material_id).stock_grams == 100

        repo.set_material_stock(material_id, 60)
        assert repo.get_material(material_id).stock_grams == 60
    finally:
        repo._materials.delete_item(item=material_id, partition_key=material_id)


def test_order_and_movement_round_trip_against_real_account(repo: CosmosRepository):
    order_id = _unique_id("order")
    variant_id = _unique_id("variant")
    order = Order(
        id=order_id, code=f"CODE-{order_id}", customer_name="Cliente de integración",
        items=[OrderItem(variant_id=variant_id, quantity=1, unit_price_cents=1000)],
        total_cents=1000, status="confirmado", created_at="2026-09-26T00:00:00.000Z",
    )
    movement = StockMovement(
        id=_unique_id("movement"), target_type="variant", target_id=variant_id,
        delta=-1, reason="venta", note=None, created_at="2026-09-26T00:00:00.000Z",
    )
    repo.save_order(order)
    repo.add_movement(movement)
    try:
        fetched_order = repo.get_order(order_id)
        assert fetched_order is not None
        assert fetched_order.total_cents == 1000
        assert repo.count_orders() >= 1

        movements = repo.list_movements(variant_id)
        assert len(movements) == 1
        assert movements[0].delta == -1
    finally:
        repo._orders.delete_item(item=order_id, partition_key=order_id)
        repo._movements.delete_item(item=movement.id, partition_key=variant_id)
