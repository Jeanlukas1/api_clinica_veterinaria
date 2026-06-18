"""
app/models/tutor.py
────────────────────
Model SQLAlchemy 2.0 para a entidade Tutor.

Decisões de design:
  - UUID como PK (não sequencial) → evita enumeração de recursos
  - cpf e email com UNIQUE → garantia de unicidade no BD além da validação
  - ativo=True (soft delete) → preserva histórico e integridade referencial
  - Campos de auditoria via TimestampMixin
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Tutor(Base, TimestampMixin):
    __tablename__ = "tutores"

    __table_args__ = (
        UniqueConstraint("cpf",   name="uq_tutores_cpf"),
        UniqueConstraint("email", name="uq_tutores_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    cpf: Mapped[str] = mapped_column(String(14), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    telefone: Mapped[str] = mapped_column(String(20), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ─── Relacionamentos ──────────────────────────────────────────────────────
    animais: Mapped[list["Animal"]] = relationship(  # noqa: F821
        "Animal",
        back_populates="tutor",
        foreign_keys="Animal.tutor_id",
        lazy="select",
    )
    transferencias_como_origem: Mapped[list["TransferenciaAnimal"]] = relationship(  # noqa: F821
        "TransferenciaAnimal",
        back_populates="tutor_origem",
        foreign_keys="TransferenciaAnimal.tutor_origem_id",
        lazy="select",
    )
    transferencias_como_destino: Mapped[list["TransferenciaAnimal"]] = relationship(  # noqa: F821
        "TransferenciaAnimal",
        back_populates="tutor_destino",
        foreign_keys="TransferenciaAnimal.tutor_destino_id",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Tutor id={self.id} nome={self.nome!r} cpf={self.cpf!r}>"
