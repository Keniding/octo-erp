"""Repositorio real contra Azure Cosmos DB for NoSQL — la única fuente de verdad en
producción (ver docs/decisions/004-agente-ia-mcp-cosmosdb.md). Sin connection string ni
key: autenticación con DefaultAzureCredential (Managed Identity en Azure, tu sesión de
`az login` en local) — mismo patrón que ya usa oraculo/web/backend.py contra Foundry.

Esquema (containers y partition keys), justificado en
oraculo/docs/10-especificacion-2-agente-octo-erp.md sección 10.5:
    products   pk /id           — point-reads por producto
    variants   pk /productId    — "variantes de este producto" es la consulta dominante
    materials  pk /id           — catálogo chico, point-reads
    orders     pk /id           — point-reads por pedido
    movements  pk /targetId     — "historial de esta variante/material" es la consulta dominante

NOTA: esta implementación no se ejecutó contra una cuenta de Cosmos DB real en esta sesión
(sandbox sin credenciales de Azure) — está escrita siguiendo la API real del SDK
`azure-cosmos`, pero su verificación end-to-end queda pendiente de un entorno con acceso a
Azure. Lo que SÍ está probado con tests reales es domain/service.py contra
InMemoryRepository, que implementa el mismo Protocol — ver tests/test_service.py.
"""

from __future__ import annotations

import os
from dataclasses import asdict

from azure.cosmos import ContainerProxy, CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

from ..domain.types import Material, Order, OrderItem, Product, ProductVariant, StockMovement


def _product_to_doc(p: Product) -> dict:
    doc = asdict(p)
    doc["imageUrl"] = doc.pop("image_url")
    doc["createdAt"] = doc.pop("created_at")
    return doc


def _doc_to_product(doc: dict) -> Product:
    return Product(
        id=doc["id"], name=doc["name"], description=doc["description"],
        category=doc["category"], created_at=doc["createdAt"],
        image_url=doc.get("imageUrl"),
    )


def _variant_to_doc(v: ProductVariant) -> dict:
    return {
        "id": v.id, "productId": v.product_id, "name": v.name, "sku": v.sku,
        "priceCents": v.price_cents, "materialId": v.material_id,
        "weightGrams": v.weight_grams, "stockUnits": v.stock_units,
        "reorderThreshold": v.reorder_threshold,
    }


def _doc_to_variant(doc: dict) -> ProductVariant:
    return ProductVariant(
        id=doc["id"], product_id=doc["productId"], name=doc["name"], sku=doc["sku"],
        price_cents=doc["priceCents"], material_id=doc["materialId"],
        weight_grams=doc["weightGrams"], stock_units=doc["stockUnits"],
        reorder_threshold=doc["reorderThreshold"],
    )


def _material_to_doc(m: Material) -> dict:
    return {
        "id": m.id, "name": m.name, "type": m.type, "colorHex": m.color_hex,
        "costPerGramCents": m.cost_per_gram_cents, "stockGrams": m.stock_grams,
        "reorderThresholdGrams": m.reorder_threshold_grams,
    }


def _doc_to_material(doc: dict) -> Material:
    return Material(
        id=doc["id"], name=doc["name"], type=doc["type"], color_hex=doc["colorHex"],
        cost_per_gram_cents=doc["costPerGramCents"], stock_grams=doc["stockGrams"],
        reorder_threshold_grams=doc["reorderThresholdGrams"],
    )


def _order_to_doc(o: Order) -> dict:
    return {
        "id": o.id, "code": o.code, "customerName": o.customer_name,
        "items": [
            {"variantId": i.variant_id, "quantity": i.quantity, "unitPriceCents": i.unit_price_cents}
            for i in o.items
        ],
        "totalCents": o.total_cents, "status": o.status, "createdAt": o.created_at,
    }


def _doc_to_order(doc: dict) -> Order:
    return Order(
        id=doc["id"], code=doc["code"], customer_name=doc["customerName"],
        items=[
            OrderItem(variant_id=i["variantId"], quantity=i["quantity"], unit_price_cents=i["unitPriceCents"])
            for i in doc["items"]
        ],
        total_cents=doc["totalCents"], status=doc["status"], created_at=doc["createdAt"],
    )


def _movement_to_doc(m: StockMovement) -> dict:
    return {
        "id": m.id, "targetType": m.target_type, "targetId": m.target_id,
        "delta": m.delta, "reason": m.reason, "note": m.note, "createdAt": m.created_at,
    }


def _doc_to_movement(doc: dict) -> StockMovement:
    return StockMovement(
        id=doc["id"], target_type=doc["targetType"], target_id=doc["targetId"],
        delta=doc["delta"], reason=doc["reason"], note=doc.get("note"),
        created_at=doc["createdAt"],
    )


class CosmosRepository:
    """Implementa el mismo Protocol que InMemoryRepository (domain/repository.py) — no hay
    herencia formal (Protocol es estructural), pero el mismo conjunto exacto de métodos."""

    def __init__(self, *, endpoint: str | None = None, database_name: str = "octo-erp") -> None:
        endpoint = endpoint or os.environ["COSMOS_ENDPOINT"]
        credential = DefaultAzureCredential()
        self._client = CosmosClient(endpoint, credential=credential)
        self._db = self._client.get_database_client(database_name)
        self._products: ContainerProxy = self._db.get_container_client("products")
        self._variants: ContainerProxy = self._db.get_container_client("variants")
        self._materials: ContainerProxy = self._db.get_container_client("materials")
        self._orders: ContainerProxy = self._db.get_container_client("orders")
        self._movements: ContainerProxy = self._db.get_container_client("movements")

    @staticmethod
    def provision_database(endpoint: str, credential=None, database_name: str = "octo-erp") -> None:
        """Crea la base y los 5 containers si no existen (idempotente). Uso: setup inicial
        o tests de integración contra una cuenta real/emulador — no se llama en producción
        normal (la infra se crea con Bicep, ver oraculo/docs/10-..., sección 10.11)."""
        client = CosmosClient(endpoint, credential=credential or DefaultAzureCredential())
        db = client.create_database_if_not_exists(id=database_name)
        db.create_container_if_not_exists(id="products", partition_key=PartitionKey(path="/id"))
        db.create_container_if_not_exists(id="variants", partition_key=PartitionKey(path="/productId"))
        db.create_container_if_not_exists(id="materials", partition_key=PartitionKey(path="/id"))
        db.create_container_if_not_exists(id="orders", partition_key=PartitionKey(path="/id"))
        db.create_container_if_not_exists(id="movements", partition_key=PartitionKey(path="/targetId"))

    # -- products --
    def list_products(self) -> list[Product]:
        return [_doc_to_product(d) for d in self._products.read_all_items()]

    def get_product(self, product_id: str) -> Product | None:
        try:
            doc = self._products.read_item(item=product_id, partition_key=product_id)
        except CosmosResourceNotFoundError:
            return None
        return _doc_to_product(doc)

    def save_product(self, product: Product) -> None:
        self._products.upsert_item(_product_to_doc(product))

    # -- variants --
    def list_variants(self, product_id: str | None = None) -> list[ProductVariant]:
        if product_id is not None:
            docs = self._variants.query_items(
                query="SELECT * FROM c WHERE c.productId = @pid",
                parameters=[{"name": "@pid", "value": product_id}],
                partition_key=product_id,
            )
        else:
            docs = self._variants.read_all_items()
        return [_doc_to_variant(d) for d in docs]

    def get_variant(self, variant_id: str) -> ProductVariant | None:
        # variants está particionado por productId, no por id -> point-read directo no
        # alcanza con solo el id; se resuelve con una cross-partition query (barata para
        # este volumen de catálogo). Si el volumen creciera mucho, conviene agregar un
        # segundo índice (ej. un container "variant_lookup" id->productId) — no
        # justificado todavía para una figura/pedidos de este tamaño.
        results = list(
            self._variants.query_items(
                query="SELECT * FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": variant_id}],
                enable_cross_partition_query=True,
            )
        )
        return _doc_to_variant(results[0]) if results else None

    def save_variant(self, variant: ProductVariant) -> None:
        self._variants.upsert_item(_variant_to_doc(variant))

    def set_variant_stock(self, variant_id: str, new_stock: int) -> None:
        variant = self.get_variant(variant_id)
        if variant is None:
            raise KeyError(variant_id)
        variant.stock_units = new_stock
        self.save_variant(variant)

    # -- materials --
    def list_materials(self) -> list[Material]:
        return [_doc_to_material(d) for d in self._materials.read_all_items()]

    def get_material(self, material_id: str) -> Material | None:
        try:
            doc = self._materials.read_item(item=material_id, partition_key=material_id)
        except CosmosResourceNotFoundError:
            return None
        return _doc_to_material(doc)

    def set_material_stock(self, material_id: str, new_stock: int) -> None:
        material = self.get_material(material_id)
        if material is None:
            raise KeyError(material_id)
        material.stock_grams = new_stock
        self._materials.upsert_item(_material_to_doc(material))

    # -- orders --
    def list_orders(self) -> list[Order]:
        return [_doc_to_order(d) for d in self._orders.read_all_items()]

    def get_order(self, order_id: str) -> Order | None:
        try:
            doc = self._orders.read_item(item=order_id, partition_key=order_id)
        except CosmosResourceNotFoundError:
            return None
        return _doc_to_order(doc)

    def save_order(self, order: Order) -> None:
        self._orders.upsert_item(_order_to_doc(order))

    def count_orders(self) -> int:
        result = list(
            self._orders.query_items(
                query="SELECT VALUE COUNT(1) FROM c", enable_cross_partition_query=True,
            )
        )
        return result[0] if result else 0

    # -- movements --
    def add_movement(self, movement: StockMovement) -> None:
        self._movements.create_item(_movement_to_doc(movement))

    def list_movements(self, target_id: str) -> list[StockMovement]:
        docs = self._movements.query_items(
            query="SELECT * FROM c WHERE c.targetId = @tid ORDER BY c.createdAt DESC",
            parameters=[{"name": "@tid", "value": target_id}],
            partition_key=target_id,
        )
        return [_doc_to_movement(d) for d in docs]
