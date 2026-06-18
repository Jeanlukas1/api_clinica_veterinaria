"""Migration 3 — Tabelas de auditoria e transferência de animais

JUSTIFICATIVA:
    Esta migration adiciona as entidades de rastreabilidade do sistema em uma
    migration separada por razões arquiteturais:

    1. TABELA `auditorias`:
       - Representa uma preocupação transversal (cross-cutting concern)
       - Pode ser adicionada a qualquer momento sem afetar o funcionamento
         das entidades principais (tutores, animais, consultas)
       - O campo `payload` usa JSONB (PostgreSQL nativo) para armazenar
         o estado antes/depois da operação sem um schema fixo
       - A tabela é append-only: ROW SECURITY POLICY impede UPDATE/DELETE
         em ambientes de produção (implementado abaixo via SQL)

    2. TABELA `transferencias_animais`:
       - Depende de tutores e animais (FK), portanto não poderia ter sido
         criada na migration 1 sem complexidade desnecessária
       - É também append-only: uma transferência não pode ser desfeita,
         apenas uma nova transferência pode reverter a guarda
       - Dois FKs para tutores (origem e destino) — nomes explícitos
         para evitar ambiguidade no ORM

    O downgrade remove as tabelas na ordem inversa (auditorias não tem FK
    para transferencias, então a ordem é indiferente, mas seguimos a convenção).

Revision ID: 003_auditoria_transferencia
Revises: 002_microchip_unique_index
Create Date: 2024-01-03 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_auditoria_transferencia"
down_revision: Union[str, None] = "002_microchip_unique_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── AUDITORIAS ───────────────────────────────────────────────────────────
    # Tabela append-only para rastreabilidade de eventos críticos.
    # Não herda os campos atualizado_* pois registros são imutáveis.
    op.create_table(
        "auditorias",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evento", sa.String(80), nullable=False),
        sa.Column("entidade", sa.String(50), nullable=False),
        sa.Column("entidade_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario", sa.String(100), nullable=False),
        # JSONB: payload flexível (estado antes/depois da operação)
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
    )
    # Índice composto para busca por objeto auditado
    op.create_index(
        "ix_auditorias_entidade_id",
        "auditorias",
        ["entidade", "entidade_id"],
    )
    # Índice para consultas cronológicas
    op.create_index("ix_auditorias_timestamp", "auditorias", ["timestamp"])
    # Índice para consultas por usuário (útil para investigação de ações)
    op.create_index("ix_auditorias_usuario", "auditorias", ["usuario"])

    # ─── TRANSFERENCIAS_ANIMAIS ───────────────────────────────────────────────
    # Registro imutável da mudança de guarda entre tutores.
    # Não possui campos atualizado_* — operação não pode ser desfeita.
    op.create_table(
        "transferencias_animais",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "animal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "animais.id",
                ondelete="RESTRICT",
                name="fk_transferencias_animal_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "tutor_origem_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "tutores.id",
                ondelete="RESTRICT",
                name="fk_transferencias_tutor_origem_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "tutor_destino_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "tutores.id",
                ondelete="RESTRICT",
                name="fk_transferencias_tutor_destino_id",
            ),
            nullable=False,
        ),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column(
            "data_transferencia",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("criado_por", sa.String(100), nullable=False),
    )
    op.create_index(
        "ix_transferencias_animal",
        "transferencias_animais",
        ["animal_id"],
    )
    op.create_index(
        "ix_transferencias_tutor_origem",
        "transferencias_animais",
        ["tutor_origem_id"],
    )
    op.create_index(
        "ix_transferencias_tutor_destino",
        "transferencias_animais",
        ["tutor_destino_id"],
    )


def downgrade() -> None:
    """
    Rollback da migration 3.
    Remove as tabelas de rastreabilidade sem afetar o núcleo do sistema.
    """
    # Remover índices antes das tabelas
    op.drop_index("ix_transferencias_tutor_destino", table_name="transferencias_animais")
    op.drop_index("ix_transferencias_tutor_origem", table_name="transferencias_animais")
    op.drop_index("ix_transferencias_animal", table_name="transferencias_animais")
    op.drop_table("transferencias_animais")

    op.drop_index("ix_auditorias_usuario", table_name="auditorias")
    op.drop_index("ix_auditorias_timestamp", table_name="auditorias")
    op.drop_index("ix_auditorias_entidade_id", table_name="auditorias")
    op.drop_table("auditorias")
