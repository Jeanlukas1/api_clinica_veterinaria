"""
app/models/transferencia_animal.py
────────────────────────────────────
Model SQLAlchemy 2.0 para a entidade TransferenciaAnimal.

Decisões de design:
  - Registro IMUTÁVEL — sem UPDATE nem DELETE (garantido no service)
  - data_transferencia é server_default=now() → sempre o momento exato da operação
  - dois FKs para tutores (origem e destino) com nomes explícitos para evitar
    ambiguidade no SQLAlchemy (múltiplos FKs para a mesma tabela)
  - criado_por é obrigatório (não herdado do mixin, pois não tem atualizado_*)
  - Auditoria gerada automaticamente no serviço de transferência (RN-010)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class TransferenciaAnimal(Base):
    __tablename__ = "transferencias_animais"

    __table_args__ = (
        Index("ix_transferencias_animal", "animal_id"),
        Index("ix_transferencias_tutor_origem", "tutor_origem_id"),
        Index("ix_transferencias_tutor_destino", "tutor_destino_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    animal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("animais.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tutor_origem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tutores.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tutor_destino_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tutores.id", ondelete="RESTRICT"),
        nullable=False,
    )
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    data_transferencia: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    criado_por: Mapped[str] = mapped_column(String(100), nullable=False)

    # ─── Relacionamentos ──────────────────────────────────────────────────────
    animal: Mapped["Animal"] = relationship(  # noqa: F821
        "Animal",
        back_populates="transferencias",
        foreign_keys=[animal_id],
        lazy="select",
    )
    tutor_origem: Mapped["Tutor"] = relationship(  # noqa: F821
        "Tutor",
        back_populates="transferencias_como_origem",
        foreign_keys=[tutor_origem_id],
        lazy="select",
    )
    tutor_destino: Mapped["Tutor"] = relationship(  # noqa: F821
        "Tutor",
        back_populates="transferencias_como_destino",
        foreign_keys=[tutor_destino_id],
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<TransferenciaAnimal id={self.id} animal_id={self.animal_id} "
            f"origem={self.tutor_origem_id} destino={self.tutor_destino_id}>"
        )
