"""Carga los mismos datos semilla que InMemoryRepository (repositories/seed.py) en una
cuenta real de Cosmos DB — idempotente (upsert), pensado para poder correrse de nuevo sin
duplicar datos. Sin esto, `/api/state` contra la cuenta real devuelve todo vacío (los
containers se crearon vacíos vía infra/main.bicep; nadie escribió catálogo ahí todavía).

Uso (con `az login` ya autenticado y el rol Cosmos DB Data Contributor asignado a tu
usuario, ver docs/decisions/006-ci-cd-azure-oidc.md):

    uv run python scripts/seed_cosmos.py https://octo-erp-cosmos-hrhdi4.documents.azure.com:443/
"""

from __future__ import annotations

import sys

from octo_erp_agent.repositories.cosmos import CosmosRepository
from octo_erp_agent.repositories.seed import SEED_MATERIALS, SEED_ORDERS, SEED_PRODUCTS, SEED_VARIANTS


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: uv run python scripts/seed_cosmos.py <COSMOS_ENDPOINT>", file=sys.stderr)
        raise SystemExit(1)

    endpoint = sys.argv[1]
    repo = CosmosRepository(endpoint=endpoint)

    for product in SEED_PRODUCTS:
        repo.save_product(product)
    for variant in SEED_VARIANTS:
        repo.save_variant(variant)
    for order in SEED_ORDERS:
        repo.save_order(order)
    # Material no tiene save_material en el Protocol (es un caso de seed/admin, ver
    # tests/test_cosmos_integration.py) — se escribe el documento directo al container.
    from octo_erp_agent.repositories.cosmos import _material_to_doc

    for material in SEED_MATERIALS:
        repo._materials.upsert_item(_material_to_doc(material))

    print(
        f"Sembrados {len(SEED_PRODUCTS)} productos, {len(SEED_VARIANTS)} variantes, "
        f"{len(SEED_MATERIALS)} materiales, {len(SEED_ORDERS)} pedidos en {endpoint}"
    )


if __name__ == "__main__":
    main()
