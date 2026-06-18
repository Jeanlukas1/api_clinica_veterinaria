"""
app/tests/conftest.py
──────────────────────
Fixtures globais para a suíte de testes.
Implementação completa na ETAPA 9.

Estratégia de isolamento:
  - Banco separado: clinica_veterinaria_test
  - Schema recriado a cada sessão de testes (scope="session")
  - Cada teste roda em transação revertida (rollback automático)
  - Client HTTP via httpx.AsyncClient com override de get_db
"""
from __future__ import annotations

import asyncio
import os

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.main import app
from app.database.session import get_db

# URL do banco de testes (banco separado do desenvolvimento)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://clinica_user:clinica_pass@localhost:5432/clinica_veterinaria_test",
)


# ─── Event loop ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Event loop compartilhado para toda a sessão de testes."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─── Engine e schema ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def engine_test():
    """
    Engine de testes — cria todas as tabelas antes da sessão,
    dropa ao final.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ─── Sessão isolada por teste ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def session(engine_test) -> AsyncSession:
    """
    Sessão de banco isolada por teste.
    Usa rollback automático ao final — os dados não persistem entre testes.
    """
    async_session = async_sessionmaker(engine_test, expire_on_commit=False)
    async with async_session() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()


# ─── Cliente HTTP ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncClient:
    """
    Cliente HTTP assíncrono (httpx) com banco de testes injetado.
    Sobrescreve a dependência get_db do FastAPI.
    """
    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ─── Fixtures de dados ────────────────────────────────────────────────────────
# Implementação completa na ETAPA 9

@pytest_asyncio.fixture
async def token_admin(client: AsyncClient) -> str:
    """Token JWT para usuário ADMIN (criado como fixture de seed)."""
    # TODO (ETAPA 9): criar usuário admin e retornar token
    return "stub_token_admin"


@pytest_asyncio.fixture
async def tutor_ativo(session: AsyncSession):
    """Tutor ativo para uso nos testes."""
    # TODO (ETAPA 9): implementar com dados reais
    pass


@pytest_asyncio.fixture
async def animal_ativo(session: AsyncSession, tutor_ativo):
    """Animal ativo vinculado ao tutor_ativo."""
    # TODO (ETAPA 9): implementar com dados reais
    pass


@pytest_asyncio.fixture
async def veterinario_ativo(session: AsyncSession):
    """Veterinário ativo para uso nos testes."""
    # TODO (ETAPA 9): implementar com dados reais
    pass


@pytest_asyncio.fixture
async def consulta_agendada(session: AsyncSession, animal_ativo, veterinario_ativo):
    """Consulta no status AGENDADA."""
    # TODO (ETAPA 9): implementar com dados reais
    pass
