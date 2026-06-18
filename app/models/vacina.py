"""
app/models/vacina.py
─────────────────────
Model SQLAlchemy 2.0 para a entidade Vacina.

Decisões de design:
  - consulta_id é OPCIONAL (nullable) — vacinas podem ser registradas
    fora de uma consulta formal (ex: campanha de vacinação externa)
  - data_proxima deve ser posterior à data_aplicacao → validado no service
  - índice em (animal_id, data_proxima) para consulta eficiente da próxima dose
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Vacina(Base, TimestampMixin):
    __tablename__ = "vacinas"

    __table_args__ = (
        Index("ix_vacinas_animal_proxima", "animal_id", "data_proxima"),
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
        index=True,
    )
    consulta_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consultas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nome_vacina: Mapped[str] = mapped_column(String(150), nullable=False)
    lote: Mapped[str] = mapped_column(String(50), nullable=False)
    data_aplicacao: Mapped[date] = mapped_column(Date, nullable=False)
    data_proxima: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ─── Relacionamentos ──────────────────────────────────────────────────────
    animal: Mapped["Animal"] = relationship(  # noqa: F821
        "Animal",
        back_populates="vacinas",
        lazy="select",
    )
    consulta: Mapped["Consulta | None"] = relationship(  # noqa: F821
        "Consulta",
        back_populates="vacinas",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Vacina id={self.id} nome={self.nome_vacina!r} "
            f"aplicacao={self.data_aplicacao}>"
        )
