"""Prueba end-to-end REAL del servidor MCP: levanta octo_erp_agent.mcp_server.asgi_app en
un servidor HTTP de verdad (uvicorn, en un puerto local libre) y le habla con el cliente
MCP oficial (mcp.client.streamable_http + ClientSession) — el mismo protocolo que usaría
Azure AI Foundry contra este servidor una vez desplegado. No son mocks: es una llamada MCP
real (initialize -> tools/list -> tools/call) sobre HTTP real, contra la implementación real
de las reglas de negocio (InMemoryRepository, sin Azure).
"""

from __future__ import annotations

import json
import socket
import threading
import time

import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from octo_erp_agent import mcp_server


def _tool_json(result) -> dict:
    """El servidor devuelve las tools como TextContent con un JSON serializado (ver
    octo_erp_agent/mcp_server.py, cada tool retorna un dict que el SDK MCP serializa a
    texto) — esta versión del SDK no está poblando `structured_content` automáticamente
    para tools sin output_schema declarado, así que se parsea el texto real, que es
    exactamente lo que recibiría el modelo del agente."""
    return json.loads(result.content[0].text)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server_url():
    port = _free_port()
    config = uvicorn.Config(mcp_server.asgi_app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    assert server.started, "El servidor uvicorn no arrancó a tiempo"

    yield f"http://127.0.0.1:{port}/mcp"

    server.should_exit = True
    thread.join(timeout=5)


@pytest.mark.asyncio
async def test_full_mcp_protocol_roundtrip_create_order(server_url: str):
    """Escenario real de punta a punta, todo vía protocolo MCP (no llamadas directas a
    Python): listar tools -> leer stock inicial -> crear un pedido -> confirmar que el
    stock bajó -> intentar un pedido imposible y confirmar que se rechaza con error."""
    async with streamable_http_client(server_url) as (read_stream, write_stream, *_rest):
        async with ClientSession(read_stream, write_stream) as session:
            init_result = await session.initialize()
            assert init_result.server_info.name == "octo-erp-tools"

            tools_result = await session.list_tools()
            tool_names = {t.name for t in tools_result.tools}
            assert {
                "get_catalog_summary",
                "get_variant_stock",
                "list_low_stock_variants",
                "list_low_stock_materials",
                "create_order",
                "adjust_variant_stock",
            }.issubset(tool_names)

            stock_before = await session.call_tool(
                "get_variant_stock", {"variant_id": "var-samurai-10-sin-pintar"}
            )
            assert not stock_before.is_error
            stock_before_units = _tool_json(stock_before)["stock_units"]
            assert stock_before_units == 14

            order_result = await session.call_tool(
                "create_order",
                {
                    "customer_name": "Taller Origami (test e2e MCP)",
                    "items": [{"variant_id": "var-samurai-10-sin-pintar", "quantity": 2}],
                },
            )
            assert not order_result.is_error, order_result.content
            assert _tool_json(order_result)["code"] == "ORD-1002"

            stock_after = await session.call_tool(
                "get_variant_stock", {"variant_id": "var-samurai-10-sin-pintar"}
            )
            assert not stock_after.is_error
            assert _tool_json(stock_after)["stock_units"] == stock_before_units - 2

            impossible_order = await session.call_tool(
                "create_order",
                {
                    "customer_name": "Cliente sin stock",
                    "items": [{"variant_id": "var-dragon-resina", "quantity": 999}],
                },
            )
            # la tool atrapa el error de dominio y lo devuelve como {"error": "..."} en vez
            # de romper la llamada MCP (mismo patrón que oraculo/mcp_server.py) — por eso
            # se verifica el contenido, no `is_error`.
            assert not impossible_order.is_error
            assert "insuficiente" in _tool_json(impossible_order)["error"].lower()
