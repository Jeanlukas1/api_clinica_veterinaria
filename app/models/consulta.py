"""
app/models/consulta.py
───────────────────────
Model SQLAlchemy 2.0 para a entidade Consulta.

Decisões de design:
  - status armazenado como VARCHAR — validação e transições no ConsultaService
  - diagnostico como TEXT nullable — torna-se obrigatório apenas ao concluir (RN-007)
  - índice composto em (veterinario_id, data_hora) para detecção rápida de conflitos (RN-004)
  - índice em (animal_id, data_hora) para construção eficiente do histórico clínico
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import StatusConsulta, TipoConsulta


class Consulta(Base, TimestampMixin):
    __tablename__ = "consultas"

    __table_args__ = (
        # Índice para busca de conflitos de horário por veterinário (RN-004)
        Index("ix_consultas_veterinario_data", "veterinario_id", "data_hora"),
        # Índice para montagem do histórico clínico por animal
        Index("ix_consultas_animal_data", "animal_id", "data_hora"),
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
    veterinario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("veterinarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    data_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=StatusConsulta.AGENDADA.value,
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    diagnostico: Mapped[str | None] = mapped_column(Text, nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Relacionamentos ──────────────────────────────────────────────────────
    animal: Mapped["Animal"] = relationship(  # noqa: F821
        "Animal",
        back_populates="consultas",
        lazy="select",
    )
    veterinario: Mapped["Veterinario"] = relationship(  # noqa: F821
        "Veterinario",
        back_populates="consultas",
        lazy="select",
    )
    vacinas: Mapped[list["Vacina"]] = relationship(  # noqa: F821
        "Vacina",
        back_populates="consulta",
        lazy="select",
    )

    # ─── Propriedades de domínio ──────────────────────────────────────────────
    @property
    def status_enum(self) -> StatusConsulta:
        return StatusConsulta(self.status)

    @property
    def tipo_enum(self) -> TipoConsulta:
        return TipoConsulta(self.tipo)

    @property
    def is_terminal(self) -> bool:
        """Retorna True se a consulta está em estado terminal."""
        from app.models.enums import ESTADOS_TERMINAIS
        return self.status_enum in ESTADOS_TERMINAIS

    def pode_transicionar_para(self, novo_status: StatusConsulta) -> bool:
        """Verifica se a transição de estado é válida segundo a máquina de estados."""
        from app.models.enums import TRANSICOES_VALIDAS
        return novo_status in TRANSICOES_VALIDAS.get(self.status_enum, [])

    def __repr__(self) -> str:
        return (
            f"<Consulta id={self.id} status={self.status!r} "
            f"animal_id={self.animal_id} data_hora={self.data_hora}>"
        )
