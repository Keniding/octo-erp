"""Tests reales del intérprete de comandos conversacional (agent_chat.py) contra
InMemoryRepository — sin red, sin LLM, deterministas. Cada test confirma que el "chat"
ejecuta la MISMA acción real que ya prueban test_service.py/test_mcp_server.py, no una
simulación aparte."""

from __future__ import annotations

import pytest

from octo_erp_agent import agent_chat
from octo_erp_agent.repositories.in_memory import InMemoryRepository


@pytest.fixture
def repo() -> InMemoryRepository:
    return InMemoryRepository()


def test_unrecognized_message_returns_help(repo: InMemoryRepository):
    result = agent_chat.handle_message(repo, "quiero que me cantes una canción")
    assert "no entendí" in result.reply.lower()
    assert "catálogo" in result.reply.lower()
    assert result.action is None


def test_empty_message_returns_help(repo: InMemoryRepository):
    result = agent_chat.handle_message(repo, "   ")
    assert result.action is None


def test_catalog_command(repo: InMemoryRepository):
    result = agent_chat.handle_message(repo, "catálogo")
    assert "Samurai errante" in result.reply
    assert result.action["type"] == "catalog_summary"


def test_low_stock_command_lists_dragon_variant(repo: InMemoryRepository):
    result = agent_chat.handle_message(repo, "stock bajo")
    assert "DRG-25-RES" in result.reply
    assert "var-dragon-resina" in result.action["variant_ids"]


def test_low_stock_command_when_nothing_is_low(repo: InMemoryRepository):
    # subir el stock del dragón por encima de su umbral antes de preguntar
    agent_chat.handle_message(repo, "ajustar DRG-25-RES +10")
    result = agent_chat.handle_message(repo, "stock bajo")
    assert "ninguna variante" in result.reply.lower()


def test_stock_of_known_sku(repo: InMemoryRepository):
    result = agent_chat.handle_message(repo, "stock de SAM-10-RAW")
    assert "14 unidades" in result.reply
    assert result.action == {
        "type": "stock_query", "variant_id": "var-samurai-10-sin-pintar", "stock_units": 14,
    }


def test_stock_of_unknown_sku(repo: InMemoryRepository):
    result = agent_chat.handle_message(repo, "stock de NO-EXISTE")
    assert "no encontré" in result.reply.lower()
    assert result.action is None


def test_create_order_command_actually_deducts_stock(repo: InMemoryRepository):
    result = agent_chat.handle_message(repo, "pedido SAM-10-RAW x2 para Taller Origami")
    assert result.action["type"] == "order_created"
    assert "ORD-1002" in result.reply
    # la prueba real: el repositorio -no solo el texto de respuesta- refleja el descuento
    variant = repo.get_variant("var-samurai-10-sin-pintar")
    assert variant.stock_units == 12  # 14 - 2
    order = repo.get_order(result.action["order_id"])
    assert order.customer_name == "Taller Origami"


def test_create_order_command_is_case_insensitive_and_tolerates_spacing(repo: InMemoryRepository):
    result = agent_chat.handle_message(repo, "PEDIDO sam-10-raw x 3 PARA  Cliente Nuevo ")
    assert result.action["type"] == "order_created"
    assert repo.get_variant("var-samurai-10-sin-pintar").stock_units == 11  # 14 - 3


def test_create_order_command_rejects_insufficient_stock_without_mutating(repo: InMemoryRepository):
    result = agent_chat.handle_message(repo, "pedido DRG-25-RES x999 para Cliente sin stock")
    assert result.action is None
    assert "no pude crear el pedido" in result.reply.lower()
    assert repo.get_variant("var-dragon-resina").stock_units == 2  # sin cambios


def test_create_order_command_unknown_sku(repo: InMemoryRepository):
    result = agent_chat.handle_message(repo, "pedido NO-EXISTE x1 para Cliente")
    assert result.action is None
    assert "no encontré" in result.reply.lower()


def test_adjust_command_increases_stock(repo: InMemoryRepository):
    result = agent_chat.handle_message(repo, "ajustar SAM-10-RAW +5")
    assert result.action == {
        "type": "stock_adjusted", "variant_id": "var-samurai-10-sin-pintar", "stock_units": 19,
    }
    assert repo.get_variant("var-samurai-10-sin-pintar").stock_units == 19


def test_adjust_command_with_named_reason(repo: InMemoryRepository):
    agent_chat.handle_message(repo, "ajustar SAM-10-RAW +5 recepcion")
    movements = repo.list_movements("var-samurai-10-sin-pintar")
    assert movements[0].reason == "recepcion"
    assert movements[0].note is None


def test_adjust_command_with_free_text_note(repo: InMemoryRepository):
    agent_chat.handle_message(repo, "ajustar SAM-10-RAW +5 reposición de emergencia del taller")
    movements = repo.list_movements("var-samurai-10-sin-pintar")
    assert movements[0].reason == "ajuste-manual"
    assert movements[0].note == "reposición de emergencia del taller"


def test_adjust_command_rejects_negative_result(repo: InMemoryRepository):
    result = agent_chat.handle_message(repo, "ajustar DRG-25-RES -10")
    assert result.action is None
    assert repo.get_variant("var-dragon-resina").stock_units == 2
