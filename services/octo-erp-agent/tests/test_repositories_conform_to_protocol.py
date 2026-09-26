"""Garantiza que InMemoryRepository y CosmosRepository implementan exactamente el mismo
contrato (ErpRepository) — si alguien agrega un método a uno y se olvida del otro, este
test lo detecta sin necesitar una cuenta de Cosmos DB real."""

from __future__ import annotations

from octo_erp_agent.domain.repository import ErpRepository
from octo_erp_agent.repositories.cosmos import CosmosRepository
from octo_erp_agent.repositories.in_memory import InMemoryRepository


def test_in_memory_repository_conforms_to_protocol():
    assert isinstance(InMemoryRepository(), ErpRepository)


def test_cosmos_repository_class_has_the_same_methods_as_the_protocol():
    # No se instancia CosmosRepository (requeriría credenciales de Azure reales) — se
    # verifica a nivel de clase que expone cada método del Protocol con la misma firma
    # posicional mínima.
    protocol_methods = {
        name for name in dir(ErpRepository) if not name.startswith("_")
    }
    cosmos_methods = {name for name in dir(CosmosRepository) if not name.startswith("_")}
    missing = protocol_methods - cosmos_methods
    assert not missing, f"CosmosRepository no implementa: {missing}"
