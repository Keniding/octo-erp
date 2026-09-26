"""Excepciones de dominio — mismo comportamiento que packages/shared/src/types.ts
(InsufficientStockError): nunca dejar que una tool MCP tumbe la llamada con un traceback,
capturar esto en la capa de tools y devolver {"error": "..."} (ver oraculo/mcp_server.py,
mismo patrón)."""

from __future__ import annotations


class InsufficientStockError(Exception):
    def __init__(self, target_id: str, available: int, requested: int):
        self.target_id = target_id
        self.available = available
        self.requested = requested
        super().__init__(
            f"Stock insuficiente para {target_id}: disponible {available}, "
            f"solicitado {requested}"
        )


class NotFoundError(Exception):
    def __init__(self, kind: str, entity_id: str):
        self.kind = kind
        self.entity_id = entity_id
        super().__init__(f"{kind} no encontrado: {entity_id}")


class ValidationError(Exception):
    pass
