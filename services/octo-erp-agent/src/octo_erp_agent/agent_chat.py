"""Motor conversacional del agente — LLM real (Azure AI Foundry, `gpt-5.4-nano`) con
tool-calling, conectado a las reglas de negocio *a través del protocolo MCP real* (no
llamadas directas a Python): cada tool que el modelo puede invocar es literalmente una tool
de `mcp_server.py`, ejecutada vía un cliente MCP (`mcp.client._memory.InMemoryTransport`)
contra el mismo servidor MCP que usa Azure AI Foundry/cualquier otro cliente MCP — sin un
segundo camino de ejecución paralelo al que ya prueba `tests/test_mcp_server.py`.

Auth: Entra ID (Managed Identity de esta Function App en producción, tu `az login` en
local) contra el recurso de Azure AI Foundry — nunca una API key, mismo patrón que
`repositories/cosmos.py` ya usa contra Cosmos DB.

Sin fallback silencioso a comandos por regex si el LLM falla — a propósito: si la llamada
al modelo falla (cuota, red, lo que sea), el chat devuelve un error honesto, nunca una
respuesta que por casualidad coincida con un patrón de regex y aparente que el modelo
entendió cuando en realidad nunca respondió — eso sería un comportamiento falso, no una demo
real. El intérprete por comandos (`_handle_message_deterministic`) solo se usa si
`AGENT_LLM_DISABLED=1` está seteado explícitamente (modo explícito sin LLM para dev/tests
sin Azure, no un fallback de fallas) — ver `test_agent_chat.py` para ese modo, y
`test_agent_chat_llm.py` para el LLM real.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession
from mcp.client._memory import InMemoryTransport
from mcp.types import Tool as MCPTool

from . import mcp_server
from .domain import service
from .domain.errors import InsufficientStockError, NotFoundError, ValidationError
from .domain.repository import ErpRepository
from .domain.types import NewOrderItemInput, StockMovementReason

logger = logging.getLogger(__name__)

_VALID_REASONS: set[StockMovementReason] = {
    "recepcion", "ajuste-manual", "venta", "merma", "produccion",
}

_HELP_TEXT = (
    "No entendí ese mensaje. Comandos que sí entiendo:\n"
    "• catálogo — lista las figuras disponibles\n"
    "• stock de <SKU> — stock actual de una variante\n"
    "• stock bajo — variantes por debajo del umbral de reposición\n"
    "• pedido <SKU> x<CANTIDAD> para <CLIENTE> — crea un pedido (descuenta stock)\n"
    "• ajustar <SKU> <+N|-N> [motivo] — ajusta stock manualmente"
)

_MUTATING_TOOLS = {"create_order", "adjust_variant_stock", "adjust_material_stock"}

_MAX_TOOL_ROUNDS = 5

_SYSTEM_PROMPT = (
    "Sos el asistente conversacional de Octo ERP, un sistema de venta de figuras impresas "
    "en 3D. Respondés en español rioplatense, corto y directo. Usás las tools disponibles "
    "para consultar o modificar datos reales — nunca inventás precios, stock ni SKUs. "
    "Antes de crear un pedido o ajustar stock, si no estás seguro de que el SKU existe, "
    "usá find_variant_by_sku primero. Si una tool devuelve {\"error\": ...}, explicá el "
    "error al usuario en lenguaje natural, no repitas el JSON crudo."
)


@dataclass(slots=True)
class AgentReply:
    reply: str
    action: dict[str, Any] | None = None


async def handle_message(repo: ErpRepository, message: str) -> AgentReply:
    text = message.strip()
    if not text:
        return AgentReply(reply=_HELP_TEXT)

    if os.environ.get("AGENT_LLM_DISABLED") != "1":
        try:
            return await _handle_message_llm(repo, text)
        except Exception:
            # Error honesto, no un fallback a regex que podría coincidir por casualidad y
            # aparentar que el modelo respondió cuando en realidad la llamada falló — ver
            # el docstring del módulo.
            logger.exception("Falló la llamada al LLM")
            return AgentReply(
                reply="No pude conectar con el modelo de IA en este momento. Probá de nuevo en un rato."
            )

    return _handle_message_deterministic(repo, text)


# -- LLM real, tool-calling vía MCP real ------------------------------------------------
# Nota importante sobre `repo` en _handle_message_llm: el parámetro se recibe pero las
# tools MCP que el modelo invoca (get_catalog_summary, create_order, etc., definidas en
# mcp_server.py) cierran sobre el singleton de módulo `mcp_server.repo`, no sobre este
# parámetro — no hay forma de inyectar un repositorio distinto sin tocar mcp_server.py.
# En producción esto nunca importa: `http_app.py` conecta `asgi_app.state.repo` al MISMO
# singleton, así que siempre son el mismo objeto. Al testear este módulo directamente,
# usar `mcp_server.repo` (no una `InMemoryRepository()` nueva) para que las aserciones
# lean del mismo repositorio que la tool realmente mutó — ver test_agent_chat_llm.py.

# Endpoint hardcodeado (no una URL secreta — la auth es 100% Entra ID/Managed Identity, sin
# key) en vez de un app setting: mismo motivo que _DEFAULT_CORS_ORIGINS en http_app.py —
# cambiar CUALQUIER app setting justo antes de un deploy dispara fallas intermitentes de
# sync-trigger en esta suscripción (ver docs/decisions/007). AGENT_OPENAI_ENDPOINT sigue
# disponible como override explícito si hace falta apuntar a otro recurso.
_DEFAULT_OPENAI_ENDPOINT = "https://octo-erp-ai.cognitiveservices.azure.com/"
_DEFAULT_OPENAI_DEPLOYMENT = "gpt-5.4-nano"


def _get_openai_client():
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import AzureOpenAI

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return AzureOpenAI(
        azure_endpoint=os.environ.get("AGENT_OPENAI_ENDPOINT", _DEFAULT_OPENAI_ENDPOINT),
        azure_ad_token_provider=token_provider,
        api_version="2024-10-21",
    )


def _mcp_tool_to_openai_schema(tool: MCPTool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


async def _handle_message_llm(repo: ErpRepository, text: str) -> AgentReply:
    client = _get_openai_client()
    deployment = os.environ.get("AGENT_OPENAI_DEPLOYMENT", _DEFAULT_OPENAI_DEPLOYMENT)

    async with InMemoryTransport(mcp_server.mcp) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_schemas = [_mcp_tool_to_openai_schema(t) for t in tools_result.tools]

            messages: list[dict] = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ]
            action: dict[str, Any] | None = None

            for _ in range(_MAX_TOOL_ROUNDS):
                response = client.chat.completions.create(
                    model=deployment, messages=messages, tools=tool_schemas,
                )
                choice = response.choices[0].message

                if not choice.tool_calls:
                    return AgentReply(reply=choice.content or _HELP_TEXT, action=action)

                messages.append(
                    {
                        "role": "assistant",
                        "content": choice.content,
                        "tool_calls": [
                            {
                                "id": tc.id, "type": "function",
                                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                            }
                            for tc in choice.tool_calls
                        ],
                    }
                )

                for tool_call in choice.tool_calls:
                    args = json.loads(tool_call.function.arguments or "{}")
                    result = await session.call_tool(tool_call.function.name, args)
                    result_text = result.content[0].text if result.content else "{}"
                    if tool_call.function.name in _MUTATING_TOOLS and not result.is_error:
                        action = {"type": tool_call.function.name, "arguments": args}
                    messages.append(
                        {"role": "tool", "tool_call_id": tool_call.id, "content": result_text}
                    )

            # Se agotaron los rounds de tool-calling sin una respuesta final en texto —
            # devolver algo útil en vez de nada, con lo último que dijo el modelo si hay.
            return AgentReply(
                reply=choice.content or "No pude terminar de procesar tu pedido, ¿podés reformularlo?",
                action=action,
            )


# -- Fallback determinístico (sin Azure) -------------------------------------------------
# Mismo comportamiento exacto que la versión anterior de este módulo — cubierto por
# test_agent_chat.py, que sigue corriendo sin tocar Azure/OpenAI.

_RE_CATALOG = re.compile(r"^(cat[aá]logo|productos|qu[eé] figuras hay)\b", re.IGNORECASE)
_RE_LOW_STOCK = re.compile(r"(stock bajo|bajo stock|qu[eé] hay que reponer|reposici[oó]n)", re.IGNORECASE)
_RE_STOCK_OF = re.compile(r"stock (?:de|del?)\s+(\S+)", re.IGNORECASE)
_RE_ORDER = re.compile(r"pedido\s+(\S+)\s*x\s*(\d+)\s+para\s+(.+)", re.IGNORECASE)
_RE_ADJUST = re.compile(r"ajustar\s+(\S+)\s+([+-]\d+)(?:\s+(.+))?", re.IGNORECASE)


def _handle_message_deterministic(repo: ErpRepository, text: str) -> AgentReply:
    if _RE_CATALOG.match(text):
        return _handle_catalog(repo)

    order_match = _RE_ORDER.search(text)
    if order_match:
        sku, quantity, customer = order_match.groups()
        return _handle_create_order(repo, sku=sku, quantity=int(quantity), customer=customer.strip())

    adjust_match = _RE_ADJUST.search(text)
    if adjust_match:
        sku, delta, reason_text = adjust_match.groups()
        return _handle_adjust(repo, sku=sku, delta=int(delta), reason_text=reason_text)

    if _RE_LOW_STOCK.search(text):
        return _handle_low_stock(repo)

    stock_match = _RE_STOCK_OF.search(text)
    if stock_match:
        return _handle_stock_of(repo, sku=stock_match.group(1))

    return AgentReply(reply=_HELP_TEXT)


def _handle_catalog(repo: ErpRepository) -> AgentReply:
    products = service.get_catalog_summary(repo)
    if not products:
        return AgentReply(reply="No hay figuras cargadas en el catálogo todavía.")
    lines = [
        f"• {p['name']} ({p['category']}) — {len(p['variants'])} variante(s)"
        for p in products
    ]
    return AgentReply(
        reply="Catálogo actual:\n" + "\n".join(lines),
        action={"type": "catalog_summary", "products": products},
    )


def _handle_low_stock(repo: ErpRepository) -> AgentReply:
    variants = service.list_low_stock_variants(repo)
    if not variants:
        return AgentReply(reply="Ninguna variante está por debajo de su umbral de reposición ahora mismo.")
    lines = [f"• {v.sku} ({v.name}): {v.stock_units} u., umbral {v.reorder_threshold}" for v in variants]
    return AgentReply(
        reply="Variantes por reponer:\n" + "\n".join(lines),
        action={"type": "low_stock", "variant_ids": [v.id for v in variants]},
    )


def _handle_stock_of(repo: ErpRepository, *, sku: str) -> AgentReply:
    variant = service.find_variant_by_sku(repo, sku)
    if variant is None:
        return AgentReply(reply=f"No encontré ninguna variante con el SKU '{sku}'.")
    return AgentReply(
        reply=f"{variant.sku} ({variant.name}) tiene {variant.stock_units} unidades en stock.",
        action={"type": "stock_query", "variant_id": variant.id, "stock_units": variant.stock_units},
    )


def _handle_create_order(repo: ErpRepository, *, sku: str, quantity: int, customer: str) -> AgentReply:
    variant = service.find_variant_by_sku(repo, sku)
    if variant is None:
        return AgentReply(reply=f"No encontré ninguna variante con el SKU '{sku}', no puedo crear el pedido.")
    try:
        order = service.create_order(
            repo,
            customer_name=customer,
            items=[NewOrderItemInput(variant_id=variant.id, quantity=quantity)],
        )
    except (InsufficientStockError, NotFoundError, ValidationError) as exc:
        return AgentReply(reply=f"No pude crear el pedido: {exc}")
    return AgentReply(
        reply=(
            f"Pedido {order.code} creado para {order.customer_name}: {quantity} × {sku}. "
            f"Total ${order.total_cents / 100:.2f}."
        ),
        action={"type": "order_created", "order_id": order.id, "order_code": order.code},
    )


def _handle_adjust(repo: ErpRepository, *, sku: str, delta: int, reason_text: str | None) -> AgentReply:
    variant = service.find_variant_by_sku(repo, sku)
    if variant is None:
        return AgentReply(reply=f"No encontré ninguna variante con el SKU '{sku}'.")

    reason: StockMovementReason = "ajuste-manual"
    note = reason_text.strip() if reason_text else None
    if note and note.replace("_", "-").lower() in _VALID_REASONS:
        reason = note.replace("_", "-").lower()  # type: ignore[assignment]
        note = None

    try:
        updated = service.adjust_variant_stock(
            repo, variant_id=variant.id, delta=delta, reason=reason, note=note,
        )
    except (InsufficientStockError, NotFoundError, ValidationError) as exc:
        return AgentReply(reply=f"No pude ajustar el stock: {exc}")
    signo = "+" if delta >= 0 else ""
    return AgentReply(
        reply=f"Stock de {sku} ajustado ({signo}{delta}). Nuevo stock: {updated.stock_units} u.",
        action={"type": "stock_adjusted", "variant_id": updated.id, "stock_units": updated.stock_units},
    )
