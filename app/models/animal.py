"""
app/models/animal.py
─────────────────────
Model SQLAlchemy 2.0 para a entidade Animal.

Decisões de design:
  - microchip com índice UNIQUE PARCIAL (WHERE microchip IS NOT NULL)
    → permite múltiplos animais sem microchip, mas garante unicidade
      quando o campo está preenchido. Criado na Migration 2.
  - data_nascimento como Date (sem hora) — relevante apenas a data
  - peso como Numeric(6,3) → ex: 999.999 kg (suficiente para qualquer espécie)
  - especie e sexo como VARCHAR com Enum Python para validação em camada de serviço
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import EspecieAnimal, SexoAnimal


class Animal(Base, TimestampMixin):
    __tablename__ = "animais"

    __table_args__ = (
        # Índice único parcial criado via Alembic Migration 2
        # UniqueConstraint em microchip é parcial: WHERE microchip IS NOT NULL
        # Não é possível expressar restrição parcial via __table_args__ simples;
        # é criada explicitamente na migration com Index(unique=True, postgresql_where=...)
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tutor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tutores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    especie: Mapped[str] = mapped_column(String(50), nullable=False)
    raca: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sexo: Mapped[str] = mapped_column(String(1), nullable=False)
    data_nascimento: Mapped[date] = mapped_column(Date, nullable=False)
    peso: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    microchip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ─── Relacionamentos ──────────────────────────────────────────────────────
    tutor: Mapped["Tutor"] = relationship(  # noqa: F821
        "Tutor",
        back_populates="animais",
        foreign_keys=[tutor_id],
        lazy="select",
    )
    consultas: Mapped[list["Consulta"]] = relationship(  # noqa: F821
        "Consulta",
        back_populates="animal",
        lazy="select",
    )
    vacinas: Mapped[list["Vacina"]] = relationship(  # noqa: F821
        "Vacina",
        back_populates="animal",
        lazy="select",
    )
    transferencias: Mapped[list["TransferenciaAnimal"]] = relationship(  # noqa: F821
        "TransferenciaAnimal",
        back_populates="animal",
        lazy="select",
    )

    # ─── Propriedades derivadas ───────────────────────────────────────────────
    @property
    def idade_anos(self) -> float:
        """Cálculo derivado: idade em anos a partir da data de nascimento."""
        from datetime import date as _date
        return (_date.today() - self.data_nascimento).days / 365.25

    @property
    def especie_enum(self) -> EspecieAnimal:
        return EspecieAnimal(self.especie)

    @property
    def sexo_enum(self) -> SexoAnimal:
        return SexoAnimal(self.sexo)

    def __repr__(self) -> str:
        return f"<Animal id={self.id} nome={self.nome!r} especie={self.especie!r}>"
