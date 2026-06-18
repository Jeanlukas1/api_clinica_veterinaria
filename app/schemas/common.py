"""
app/schemas/common.py
──────────────────────
Schemas utilitários compartilhados entre todas as entidades.
"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base com configuração compartilhada."""
    model_config = ConfigDict(
        from_attributes=True,   # habilita conversão de ORM models
        populate_by_name=True,  # aceita tanto nome do campo quanto alias
        str_strip_whitespace=True,
    )


class PaginatedResponse(BaseSchema, Generic[T]):
    """
    Resposta paginada genérica.

    Exemplo:
        PaginatedResponse[TutorResponse] para GET /tutores
    """
    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_next(self) -> bool:
        return self.offset + self.limit < self.total

    @property
    def has_prev(self) -> bool:
        return self.offset > 0


class ErrorResponse(BaseSchema):
    """
    Padrão de resposta de erro da API.

    Exemplo:
        {"error": "CONSULTA_CONFLICT", "message": "...", "details": {...}}
    """
    error: str
    message: str
    details: dict = {}


class MessageResponse(BaseSchema):
    """Resposta simples de mensagem."""
    message: str


class HealthResponse(BaseSchema):
    """Resposta do endpoint /health."""
    status: str
    version: str
    environment: str
    database: str
