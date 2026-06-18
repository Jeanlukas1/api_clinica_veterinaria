"""
app/models/auditoria.py
────────────────────────
Model SQLAlchemy 2.0 para a entidade Auditoria.

Decisões de design:
  - Tabela APPEND-ONLY: sem UPDATE nem DELETE (garantido por policy no service)
  - payload como JSONB → flexibilidade para capturar estado antes/depois sem schema fixo
  - índice composto em (entidade, entidade_id) → consulta rápida por objeto auditado
  - índice em timestamp → ordenação cronológica eficiente
  - ip_address armazenado para conformidade com LGPD
  - Não herda TimestampMixin pois não há `atualizado_em` (registro imutável)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Auditoria(Base):
    __tablename__ = "auditorias"

    __table_args__ = (
        Index("ix_auditorias_entidade_id", "entidade", "entidade_id"),
        Index("ix_auditorias_timestamp", "timestamp"),
        Index("ix_auditorias_usuario", "usuario"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    evento: Mapped[str] = mapped_column(String(80), nullable=False)
    entidade: Mapped[str] = mapped_column(String(50), nullable=False)
    entidade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    usuario: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Auditoria id={self.id} evento={self.evento!r} "
            f"entidade={self.entidade!r} ts={self.timestamp}>"
        )
