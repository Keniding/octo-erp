"""Tests reales de la API REST (rest_api.py) — request/response HTTP de verdad vía
Starlette TestClient (httpx), no llamadas directas a las funciones Python. Cada test arma
un repositorio en memoria nuevo (no el singleton de mcp_server.py) para no compartir estado
mutado con tests/test_mcp_server.py, que sí usa ese singleton."""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from octo_erp_agent.repositories.in_memory import InMemoryRepository
from octo_erp_agent.repositories.seed import SEED_PRODUCTS, SEED_VARIANTS
from octo_erp_agent.rest_api import api_routes


@pytest.fixture
def client() -> TestClient:
    app = Starlette(routes=api_routes)
    app.state.repo = InMemoryRepository()
    return TestClient(app)


def test_get_state_returns_seed_data_in_camel_case(client: TestClient):
    response = client.get("/api/state")
    assert response.status_code == 200
    body = response.json()
    assert len(body["products"]) == len(SEED_PRODUCTS)
    assert len(body["variants"]) == len(SEED_VARIANTS)
    assert body["movements"] == []
    # Shape camelCase igual a packages/shared/src/types.ts, no snake_case de Python.
    assert "imageUrl" in body["products"][0] or body["products"][0].get("imageUrl") is None
    assert "stockUnits" in body["variants"][0]


def test_create_product_then_appears_in_state(client: TestClient):
    response = client.post(
        "/api/products",
        json={
            "name": "Figura de prueba REST",
            "description": "temporal",
            "category": "Fantasia",
            "variants": [
                {
                    "name": "Única", "sku": "REST-1", "priceCents": 1000,
                    "materialId": "mat-pla-negro", "weightGrams": 50,
                    "stockUnits": 5, "reorderThreshold": 1,
                }
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["product"]["name"] == "Figura de prueba REST"
    assert len(body["variants"]) == 1

    state = client.get("/api/state").json()
    assert any(p["id"] == body["product"]["id"] for p in state["products"])


def test_create_product_without_name_returns_400(client: TestClient):
    response = client.post(
        "/api/products",
        json={"name": "", "description": "x", "category": "Fantasia", "variants": []},
    )
    assert response.status_code == 400
    assert "obligatorio" in response.json()["error"]


def test_adjust_variant_stock_round_trip(client: TestClient):
    variant_id = SEED_VARIANTS[0].id
    response = client.post(
        f"/api/variants/{variant_id}/stock-adjustments",
        json={"delta": 3, "reason": "recepcion"},
    )
    assert response.status_code == 200
    assert response.json()["stockUnits"] == SEED_VARIANTS[0].stock_units + 3


def test_adjust_variant_stock_unknown_variant_returns_404(client: TestClient):
    response = client.post(
        "/api/variants/no-existe/stock-adjustments", json={"delta": 1, "reason": "recepcion"},
    )
    assert response.status_code == 404


def test_adjust_variant_stock_insufficient_returns_409(client: TestClient):
    variant_id = SEED_VARIANTS[0].id
    response = client.post(
        f"/api/variants/{variant_id}/stock-adjustments",
        json={"delta": -(SEED_VARIANTS[0].stock_units + 1), "reason": "merma"},
    )
    assert response.status_code == 409


def test_create_order_deducts_stock(client: TestClient):
    variant_id = SEED_VARIANTS[0].id
    response = client.post(
        "/api/orders",
        json={"customerName": "Cliente REST", "items": [{"variantId": variant_id, "quantity": 2}]},
    )
    assert response.status_code == 201
    order = response.json()
    assert order["totalCents"] == SEED_VARIANTS[0].price_cents * 2

    state = client.get("/api/state").json()
    updated_variant = next(v for v in state["variants"] if v["id"] == variant_id)
    assert updated_variant["stockUnits"] == SEED_VARIANTS[0].stock_units - 2


def test_update_order_status(client: TestClient):
    order_id = client.post(
        "/api/orders",
        json={
            "customerName": "Cliente REST 2",
            "items": [{"variantId": SEED_VARIANTS[0].id, "quantity": 1}],
        },
    ).json()["id"]

    response = client.patch(f"/api/orders/{order_id}/status", json={"status": "en_produccion"})
    assert response.status_code == 200
    assert response.json()["status"] == "en_produccion"


def test_list_movements_requires_target_id(client: TestClient):
    response = client.get("/api/movements")
    assert response.status_code == 400


def test_list_movements_after_stock_adjustment(client: TestClient):
    variant_id = SEED_VARIANTS[0].id
    client.post(f"/api/variants/{variant_id}/stock-adjustments", json={"delta": 1, "reason": "recepcion"})
    response = client.get(f"/api/movements?targetId={variant_id}")
    assert response.status_code == 200
    assert len(response.json()) == 1
