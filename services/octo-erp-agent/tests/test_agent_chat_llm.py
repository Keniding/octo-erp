"""Round-trip real contra el LLM desplegado (Azure AI Foundry, `octo-erp-ai`) — no un mock.
El endpoint está hardcodeado en agent_chat.py (no depende de una env var, ver ese módulo),
así que estos tests se saltan salvo opt-in explícito (`RUN_LLM_INTEGRATION_TESTS=1`) — sin
eso correrían contra Azure real (costo + latencia real) en cada `pytest` local sin avisar.
Prueba lenguaje natural de verdad, no los comandos exactos que ya cubre test_agent_chat.py
en modo determinístico — esa es la diferencia real que justifica tener un LLM: entender
variaciones, no solo un patrón fijo.

Usa `mcp_server.repo` directamente (el singleton que las tools MCP realmente mutan, ver
la nota en agent_chat.py) en vez de una InMemoryRepository nueva."""

from __future__ import annotations

import os

import pytest

from octo_erp_agent import mcp_server
from octo_erp_agent.agent_chat import handle_message

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LLM_INTEGRATION_TESTS") != "1",
    reason="RUN_LLM_INTEGRATION_TESTS != 1 — opt-in explícito para no pegarle a Azure real en cada pytest local.",
)


async def test_natural_language_stock_query_without_exact_sku():
    """El fallback por regex exige 'stock de <SKU>' exacto — esto prueba que el LLM
    entiende la MISMA pregunta sin conocer el SKU, resolviendo por nombre vía las tools."""
    result = await handle_message(
        mcp_server.repo, "cuánto stock tiene la variante de 10cm sin pintar del samurai"
    )
    assert result.action is None  # es una consulta, no debería mutar nada
    assert "14" in result.reply or "sam-10-raw" in result.reply.lower()


async def test_natural_language_order_creates_real_order_and_deducts_stock():
    variant_id = "var-mecha-standard"
    before = mcp_server.repo.get_variant(variant_id).stock_units

    result = await handle_message(
        mcp_server.repo,
        "necesito pedir una unidad del mecha estándar para el cliente Prueba LLM",
    )

    assert result.action is not None
    assert result.action["type"] == "create_order"
    after = mcp_server.repo.get_variant(variant_id).stock_units
    assert after == before - 1


async def test_impossible_order_reports_error_in_natural_language_without_mutating():
    variant_id = "var-dragon-resina"
    before = mcp_server.repo.get_variant(variant_id).stock_units

    result = await handle_message(
        mcp_server.repo, "pedime 500 unidades del dragoncillo de resina para Cliente Imposible"
    )

    after = mcp_server.repo.get_variant(variant_id).stock_units
    assert after == before  # nunca se mutó, el stock insuficiente se rechazó
    assert result.action is None or result.action["type"] != "create_order"


async def test_agent_uses_find_variant_by_sku_tool_when_sku_is_ambiguous():
    """Cubre la tool nueva find_variant_by_sku (no existía en el intérprete por regex) —
    verificar que el SKU se resuelve correctamente antes de operar sobre él."""
    result = await handle_message(mcp_server.repo, "el SKU MEC-STD, ¿qué figura es y qué precio tiene?")
    assert "mecha" in result.reply.lower() or "46" in result.reply
