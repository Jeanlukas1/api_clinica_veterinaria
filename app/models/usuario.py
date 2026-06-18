"""
app/models/usuario.py
──────────────────────
Model SQLAlchemy 2.0 para Usuários do sistema (autenticação JWT + RBAC).

Decisões de design:
  - Separado do Tutor pois um usuário pode ser ADMIN, VETERINARIO ou RECEPCIONISTA
    sem ser tutor de nenhum animal
  - tutor_id opcional → vincula usuário ao perfil TUTOR para filtragem de dados
  - senha_hash armazena bcrypt hash — nunca senha em texto puro
  - perfil como VARCHAR → validado via PerfilUsuario enum no service
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Usuario(Base, TimestampMixin):
    __tablename__ = "usuarios"

    __table_args__ = (
        UniqueConstraint("email", name="uq_usuarios_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[str] = mapped_column(String(20), nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Vínculo opcional com entidade Tutor (para perfil TUTOR)
    tutor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tutores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Vínculo opcional com entidade Veterinario (para perfil VETERINARIO)
    veterinario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("veterinarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<Usuario id={self.id} email={self.email!r} perfil={self.perfil!r}>"
