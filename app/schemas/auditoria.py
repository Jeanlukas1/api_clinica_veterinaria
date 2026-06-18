"""
app/schemas/auditoria.py
─────────────────────────
Schemas Pydantic V2 para a entidade Auditoria.

Nota: Auditoria é append-only — só existe AuditoriaResponse (sem Create/Update público).
A criação é feita internamente pelo AuditoriaService, não por endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from app.schemas.common import BaseSchema


class AuditoriaResponse(BaseSchema):
    """Schema de resposta para registro de auditoria."""
    id: uuid.UUID
    evento: str
    entidade: str
    entidade_id: uuid.UUID
    usuario: str
    payload: dict | None
    timestamp: datetime
    ip_address: str | None


class AuditoriaFiltros(BaseSchema):
    """Parâmetros de filtro para listagem de auditoria."""
    entidade: str | None = None
    entidade_id: uuid.UUID | None = None
    usuario: str | None = None
    evento: str | None = None
    data_inicio: datetime | None = None
    data_fim: datetime | None = None
    limit: int = 50
    offset: int = 0
