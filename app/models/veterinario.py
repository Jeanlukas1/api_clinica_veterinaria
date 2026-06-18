"""
app/models/veterinario.py
──────────────────────────
Model SQLAlchemy 2.0 para a entidade Veterinário.

Decisões de design:
  - CRMV único no BD (UniqueConstraint)
  - especialidade armazenada como VARCHAR — validada via enum na camada de serviço
  - ativo = soft delete
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Veterinario(Base, TimestampMixin):
    __tablename__ = "veterinarios"

    __table_args__ = (
        UniqueConstraint("crmv", name="uq_veterinarios_crmv"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    crmv: Mapped[str] = mapped_column(String(20), nullable=False)
    especialidade: Mapped[str] = mapped_column(String(80), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ─── Relacionamentos ──────────────────────────────────────────────────────
    consultas: Mapped[list["Consulta"]] = relationship(  # noqa: F821
        "Consulta",
        back_populates="veterinario",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Veterinario id={self.id} nome={self.nome!r} crmv={self.crmv!r}>"
