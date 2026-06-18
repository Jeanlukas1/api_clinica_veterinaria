"""
app/tests/conftest.py
──────────────────────
Fixtures globais para a suíte de testes.

Estratégia de isolamento:
  - Banco de testes separado: clinica_veterinaria_test
  - Schema criado/destruído por sessão de teste (scope="session")
  - Cada teste roda em transação que é revertida no final (rollback automático)
  - httpx.AsyncClient com override de get_db → banco isolado
  - Fixtures criam dados reais para os testes de integração
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_token_pair, hash_password
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.animal import Animal
from app.models.auditoria import Auditoria
from app.models.consulta import Consulta
from app.models.enums import (
    EspecialidadeVeterinario,
    EspecieAnimal,
    PerfilUsuario,
    SexoAnimal,
    StatusConsulta,
    TipoConsulta,
)
from app.models.tutor import Tutor
from app.models.usuario import Usuario
from app.models.vacina import Vacina
from app.models.veterinario import Veterinario

# ─── Configuração do banco de testes ─────────────────────────────────────────

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


# ─── Engine ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def engine_test():
    """
    Engine de testes — recria o schema completo antes da sessão.
    Dropa tudo ao final para limpeza.
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
    Sessão de banco com rollback automático após cada teste.
    Garante isolamento total — dados não persistem entre testes.
    """
    factory = async_sessionmaker(engine_test, expire_on_commit=False)
    async with factory() as sess:
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


# ─── Fixtures de usuário e token ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def usuario_admin(session: AsyncSession) -> Usuario:
    """Usuário ADMIN para autenticação nos testes."""
    usuario = Usuario(
        nome="Admin Teste",
        email="admin@test.com",
        senha_hash=hash_password("Admin@123456"),
        perfil=PerfilUsuario.ADMIN.value,
        ativo=True,
    )
    session.add(usuario)
    await session.flush()
    return usuario


@pytest_asyncio.fixture
async def usuario_veterinario(session: AsyncSession, veterinario_ativo: Veterinario) -> Usuario:
    """Usuário VETERINARIO vinculado a um veterinário."""
    usuario = Usuario(
        nome="Vet Teste",
        email="vet@test.com",
        senha_hash=hash_password("Vet@123456"),
        perfil=PerfilUsuario.VETERINARIO.value,
        veterinario_id=veterinario_ativo.id,
        ativo=True,
    )
    session.add(usuario)
    await session.flush()
    return usuario


@pytest_asyncio.fixture
def token_admin(usuario_admin: Usuario) -> str:
    """Bearer token JWT do usuário ADMIN."""
    pair = create_token_pair(usuario_admin.email, usuario_admin.perfil)
    return pair.access_token


@pytest_asyncio.fixture
def headers_admin(token_admin: str) -> dict:
    """Headers HTTP com token ADMIN."""
    return {"Authorization": f"Bearer {token_admin}"}


# ─── Fixtures de domínio ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def tutor_ativo(session: AsyncSession) -> Tutor:
    """Tutor ativo para uso nos testes."""
    tutor = Tutor(
        nome="Carlos Silva",
        cpf="529.982.247-25",
        email="carlos@test.com",
        telefone="(11) 99999-1111",
        ativo=True,
        criado_por="fixture",
    )
    session.add(tutor)
    await session.flush()
    return tutor


@pytest_asyncio.fixture
async def tutor_secundario(session: AsyncSession) -> Tutor:
    """Segundo tutor ativo para testes de transferência."""
    tutor = Tutor(
        nome="Maria Souza",
        cpf="048.576.853-03",
        email="maria@test.com",
        telefone="(11) 99999-2222",
        ativo=True,
        criado_por="fixture",
    )
    session.add(tutor)
    await session.flush()
    return tutor


@pytest_asyncio.fixture
async def veterinario_ativo(session: AsyncSession) -> Veterinario:
    """Veterinário ativo para uso nos testes."""
    vet = Veterinario(
        nome="Dr. Roberto Lima",
        crmv="CRMV-SP-12345",
        especialidade=EspecialidadeVeterinario.CLINICA_GERAL.value,
        ativo=True,
        criado_por="fixture",
    )
    session.add(vet)
    await session.flush()
    return vet


@pytest_asyncio.fixture
async def animal_ativo(session: AsyncSession, tutor_ativo: Tutor) -> Animal:
    """Animal ativo vinculado ao tutor_ativo."""
    animal = Animal(
        tutor_id=tutor_ativo.id,
        nome="Rex",
        especie=EspecieAnimal.CANINO.value,
        raca="Golden Retriever",
        sexo=SexoAnimal.MACHO.value,
        data_nascimento=date(2020, 5, 10),
        peso=Decimal("28.5"),
        microchip="ABC1234567890",
        ativo=True,
        criado_por="fixture",
    )
    session.add(animal)
    await session.flush()
    return animal


@pytest_asyncio.fixture
async def animal_sem_microchip(session: AsyncSession, tutor_ativo: Tutor) -> Animal:
    """Animal ativo sem microchip (para testar unicidade parcial)."""
    animal = Animal(
        tutor_id=tutor_ativo.id,
        nome="Mimi",
        especie=EspecieAnimal.FELINO.value,
        sexo=SexoAnimal.FEMEA.value,
        data_nascimento=date(2021, 3, 15),
        peso=Decimal("4.2"),
        microchip=None,
        ativo=True,
        criado_por="fixture",
    )
    session.add(animal)
    await session.flush()
    return animal


@pytest_asyncio.fixture
async def consulta_agendada(
    session: AsyncSession, animal_ativo: Animal, veterinario_ativo: Veterinario
) -> Consulta:
    """Consulta no status AGENDADA."""
    consulta = Consulta(
        animal_id=animal_ativo.id,
        veterinario_id=veterinario_ativo.id,
        data_hora=datetime.now(timezone.utc) + timedelta(days=1),
        status=StatusConsulta.AGENDADA.value,
        tipo=TipoConsulta.ROTINA.value,
        criado_por="fixture",
    )
    session.add(consulta)
    await session.flush()
    return consulta


@pytest_asyncio.fixture
async def consulta_confirmada(
    session: AsyncSession, animal_ativo: Animal, veterinario_ativo: Veterinario
) -> Consulta:
    """Consulta no status CONFIRMADA."""
    consulta = Consulta(
        animal_id=animal_ativo.id,
        veterinario_id=veterinario_ativo.id,
        data_hora=datetime.now(timezone.utc) + timedelta(days=2),
        status=StatusConsulta.CONFIRMADA.value,
        tipo=TipoConsulta.ROTINA.value,
        criado_por="fixture",
    )
    session.add(consulta)
    await session.flush()
    return consulta


@pytest_asyncio.fixture
async def consulta_em_andamento(
    session: AsyncSession, animal_ativo: Animal, veterinario_ativo: Veterinario
) -> Consulta:
    """Consulta no status EM_ANDAMENTO."""
    consulta = Consulta(
        animal_id=animal_ativo.id,
        veterinario_id=veterinario_ativo.id,
        data_hora=datetime.now(timezone.utc) + timedelta(days=3),
        status=StatusConsulta.EM_ANDAMENTO.value,
        tipo=TipoConsulta.ROTINA.value,
        criado_por="fixture",
    )
    session.add(consulta)
    await session.flush()
    return consulta


@pytest_asyncio.fixture
async def consulta_concluida(
    session: AsyncSession, animal_ativo: Animal, veterinario_ativo: Veterinario
) -> Consulta:
    """Consulta no status CONCLUIDA (estado terminal)."""
    consulta = Consulta(
        animal_id=animal_ativo.id,
        veterinario_id=veterinario_ativo.id,
        data_hora=datetime.now(timezone.utc) - timedelta(days=1),
        status=StatusConsulta.CONCLUIDA.value,
        tipo=TipoConsulta.ROTINA.value,
        diagnostico="Diagnóstico de teste — animal saudável.",
        criado_por="fixture",
    )
    session.add(consulta)
    await session.flush()
    return consulta
