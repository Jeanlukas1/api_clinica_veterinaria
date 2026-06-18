"""Migration 2 — Índice único parcial no campo microchip da tabela animais

JUSTIFICATIVA:
    O microchip é um identificador físico implantado no animal (padrão ISO 11784/11785).
    Sua unicidade é uma regra de negócio (RN-003), porém o campo é OPCIONAL:
    animais jovens ou sem registro podem não possuir microchip ainda.

    Um UNIQUE CONSTRAINT convencional bloquearia múltiplos NULLs, pois NULL ≠ NULL
    em PostgreSQL para efeitos de unicidade (ISO SQL padrão).

    SOLUÇÃO: Índice único PARCIAL com condição WHERE microchip IS NOT NULL.
    → Apenas valores não-nulos participam do índice
    → Múltiplos animais podem ter microchip=NULL simultaneamente
    → Dois animais NÃO podem ter o mesmo microchip quando ambos estão preenchidos

    Esta é uma migration separada da estrutura inicial para demonstrar:
    1. Adição incremental de otimizações/constraints sem recriar tabelas
    2. Uso de índices parciais avançados do PostgreSQL
    3. Separação de responsabilidades entre migrations

    O downgrade remove o índice sem afetar os dados.

Revision ID: 002_microchip_unique_index
Revises: 001_initial
Create Date: 2024-01-02 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_microchip_unique_index"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Índice único parcial: garante unicidade do microchip apenas para
    # animais que possuem o campo preenchido (WHERE microchip IS NOT NULL).
    # Isso permite múltiplos registros com microchip=NULL sem violação.
    op.execute(
        """
        CREATE UNIQUE INDEX uix_animais_microchip_not_null
        ON animais (microchip)
        WHERE microchip IS NOT NULL;
        """
    )


def downgrade() -> None:
    # Remove apenas o índice — os dados não são afetados.
    op.execute("DROP INDEX IF EXISTS uix_animais_microchip_not_null;")
