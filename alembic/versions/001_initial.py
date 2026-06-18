"""Migration 1 — Estrutura inicial: tutores, animais, veterinarios, consultas, vacinas, usuarios

JUSTIFICATIVA:
    Esta migration cria o núcleo do domínio com as entidades principais do sistema.
    A ordem de criação respeita as dependências de FK:
        tutores → animais → consultas → vacinas
        veterinarios → consultas
        usuarios (independente, mas referencia tutores e veterinarios)

    Decisões técnicas:
    - UUID como PK em todas as tabelas: evita enumeração de recursos via ID sequencial,
      compatível com sistemas distribuídos e seguro para exposição em APIs públicas.
    - TIMESTAMPTZ em todos os campos de data/hora: garante consistência em diferentes
      fusos horários (UTC internamente, conversão na apresentação).
    - BOOLEAN ativo=TRUE como soft delete: dados médicos não devem ser apagados
      fisicamente por questões de auditoria, histórico e integridade referencial.
    - ON DELETE RESTRICT nas FKs principais: impede exclusão de pai com filhos,
      forçando o uso do soft delete e preservando integridade.

Revision ID: 001_initial
Revises: —
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── TUTORES ──────────────────────────────────────────────────────────────
    op.create_table(
        "tutores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("cpf", sa.String(14), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("telefone", sa.String(20), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        # Campos de auditoria
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("criado_por", sa.String(100), nullable=True),
        sa.Column("atualizado_por", sa.String(100), nullable=True),
    )
    op.create_unique_constraint("uq_tutores_cpf", "tutores", ["cpf"])
    op.create_unique_constraint("uq_tutores_email", "tutores", ["email"])

    # ─── VETERINARIOS ─────────────────────────────────────────────────────────
    op.create_table(
        "veterinarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("crmv", sa.String(20), nullable=False),
        sa.Column("especialidade", sa.String(80), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("criado_por", sa.String(100), nullable=True),
        sa.Column("atualizado_por", sa.String(100), nullable=True),
    )
    op.create_unique_constraint("uq_veterinarios_crmv", "veterinarios", ["crmv"])

    # ─── ANIMAIS ──────────────────────────────────────────────────────────────
    op.create_table(
        "animais",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tutor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tutores.id", ondelete="RESTRICT", name="fk_animais_tutor_id"),
            nullable=False,
        ),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("especie", sa.String(50), nullable=False),
        sa.Column("raca", sa.String(100), nullable=True),
        sa.Column("sexo", sa.String(1), nullable=False),
        sa.Column("data_nascimento", sa.Date(), nullable=False),
        sa.Column("peso", sa.Numeric(6, 3), nullable=False),
        sa.Column("microchip", sa.String(50), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("criado_por", sa.String(100), nullable=True),
        sa.Column("atualizado_por", sa.String(100), nullable=True),
    )
    op.create_index("ix_animais_tutor_id", "animais", ["tutor_id"])

    # ─── CONSULTAS ────────────────────────────────────────────────────────────
    op.create_table(
        "consultas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "animal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("animais.id", ondelete="RESTRICT", name="fk_consultas_animal_id"),
            nullable=False,
        ),
        sa.Column(
            "veterinario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "veterinarios.id", ondelete="RESTRICT", name="fk_consultas_veterinario_id"
            ),
            nullable=False,
        ),
        sa.Column("data_hora", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="AGENDADA"),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("diagnostico", sa.Text(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("criado_por", sa.String(100), nullable=True),
        sa.Column("atualizado_por", sa.String(100), nullable=True),
    )
    # Índice composto para detecção de conflitos de horário (RN-004)
    op.create_index(
        "ix_consultas_veterinario_data",
        "consultas",
        ["veterinario_id", "data_hora"],
    )
    # Índice para construção do histórico clínico por animal
    op.create_index(
        "ix_consultas_animal_data",
        "consultas",
        ["animal_id", "data_hora"],
    )

    # ─── VACINAS ──────────────────────────────────────────────────────────────
    op.create_table(
        "vacinas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "animal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("animais.id", ondelete="RESTRICT", name="fk_vacinas_animal_id"),
            nullable=False,
        ),
        sa.Column(
            "consulta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "consultas.id", ondelete="SET NULL", name="fk_vacinas_consulta_id"
            ),
            nullable=True,
        ),
        sa.Column("nome_vacina", sa.String(150), nullable=False),
        sa.Column("lote", sa.String(50), nullable=False),
        sa.Column("data_aplicacao", sa.Date(), nullable=False),
        sa.Column("data_proxima", sa.Date(), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("criado_por", sa.String(100), nullable=True),
        sa.Column("atualizado_por", sa.String(100), nullable=True),
    )
    op.create_index("ix_vacinas_animal_id", "vacinas", ["animal_id"])
    op.create_index("ix_vacinas_consulta_id", "vacinas", ["consulta_id"])
    op.create_index(
        "ix_vacinas_animal_proxima",
        "vacinas",
        ["animal_id", "data_proxima"],
    )

    # ─── USUARIOS ─────────────────────────────────────────────────────────────
    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("perfil", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column(
            "tutor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tutores.id", ondelete="SET NULL", name="fk_usuarios_tutor_id"),
            nullable=True,
        ),
        sa.Column(
            "veterinario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "veterinarios.id", ondelete="SET NULL", name="fk_usuarios_veterinario_id"
            ),
            nullable=True,
        ),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("criado_por", sa.String(100), nullable=True),
        sa.Column("atualizado_por", sa.String(100), nullable=True),
    )
    op.create_unique_constraint("uq_usuarios_email", "usuarios", ["email"])
    op.create_index("ix_usuarios_tutor_id", "usuarios", ["tutor_id"])
    op.create_index("ix_usuarios_veterinario_id", "usuarios", ["veterinario_id"])


def downgrade() -> None:
    """
    Rollback completo da migration 1.
    A ordem inversa respeita as dependências de FK.
    """
    # Tabelas dependentes primeiro
    op.drop_table("usuarios")
    op.drop_table("vacinas")
    op.drop_table("consultas")
    op.drop_table("animais")
    # Tabelas raiz por último
    op.drop_table("veterinarios")
    op.drop_table("tutores")
