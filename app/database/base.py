"""
app/database/base.py
────────────────────
Base declarativa do SQLAlchemy 2.0 com campos de auditoria comuns.
Todos os models da aplicação herdam de `Base` e opcionalmente de `TimestampMixin`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa compartilhada por todos os models."""
    pass


class TimestampMixin:
    """
    Mixin com campos de auditoria de tempo e usuário.
    Adicionado a todas as entidades principais do domínio.
    """
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    criado_por: Mapped[str | None] = mapped_column(String(100), nullable=True)
    atualizado_por: Mapped[str | None] = mapped_column(String(100), nullable=True)


def generate_uuid() -> str:
    return str(uuid.uuid4())
