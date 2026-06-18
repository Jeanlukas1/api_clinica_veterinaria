"""
alembic/env.py
───────────────
Configuração do ambiente Alembic.

Decisões de design:
  - Usa DATABASE_URL_SYNC (psycopg2) pois Alembic não suporta drivers async
  - Importa todos os models via `app.models` para que o autogenerate
    detecte todas as tabelas automaticamente
  - include_schemas=True para suporte a múltiplos schemas no futuro
  - compare_type=True para detectar alterações de tipo de coluna
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ─── Importar Base e todos os models ─────────────────────────────────────────
# IMPORTANTE: esta importação deve vir antes de qualquer uso de target_metadata
from app.database.base import Base
import app.models  # noqa: F401 — importa todos os models para autogenerate

# ─── Configuração do Alembic ──────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata alvo para autogenerate
target_metadata = Base.metadata

# ─── URL do banco via variável de ambiente ────────────────────────────────────
def get_url() -> str:
    """
    Lê DATABASE_URL_SYNC do ambiente (injetado pelo docker-compose ou .env).
    Fallback para o valor do alembic.ini.
    """
    url = os.getenv("DATABASE_URL_SYNC")
    if url:
        return url
    return config.get_main_option("sqlalchemy.url")


# ─── Modo offline (sem conexão — gera SQL puro) ───────────────────────────────
def run_migrations_offline() -> None:
    """
    Executa migrations em modo offline.
    Útil para gerar scripts SQL para review antes de aplicar.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_schemas=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


# ─── Modo online (conexão real ao banco) ─────────────────────────────────────
def run_migrations_online() -> None:
    """
    Executa migrations com conexão real ao PostgreSQL.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # NullPool é recomendado para migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_schemas=True,
            render_as_batch=False,
        )

        with context.begin_transaction():
            context.run_migrations()


# ─── Entry point ─────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
