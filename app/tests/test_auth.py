"""
app/tests/test_auth.py
───────────────────────
Testes de autenticação e RBAC.

Casos cobertos:
  TC-027: Login com credenciais válidas retorna par de tokens
  TC-028: Login com senha errada retorna 401
  TC-029: Acesso a endpoint protegido sem token retorna 401
  TC-030: Perfil sem permissão retorna 403 (RBAC)
  TC-031: Refresh token renova par de tokens
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_token_pair, hash_password
from app.models.enums import PerfilUsuario
from app.models.tutor import Tutor
from app.models.usuario import Usuario


pytestmark = pytest.mark.asyncio


class TestLogin:
    """TC-027 / TC-028 — Autenticação."""

    async def test_TC027_login_valido_retorna_tokens(
        self, client: AsyncClient, usuario_admin: Usuario
    ) -> None:
        """TC-027: Login com credenciais válidas deve retornar access + refresh token."""
        response = await client.post(
            "/auth/login",
            data={
                "username": usuario_admin.email,
                "password": "Admin@123456",
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    async def test_TC028_senha_errada_retorna_401(
        self, client: AsyncClient, usuario_admin: Usuario
    ) -> None:
        """TC-028: Credenciais inválidas devem retornar 401."""
        response = await client.post(
            "/auth/login",
            data={
                "username": usuario_admin.email,
                "password": "SenhaErrada@99",
            },
        )
        assert response.status_code == 401
        assert response.json()["error"] == "CREDENCIAIS_INVALIDAS"

    async def test_TC028b_email_inexistente_retorna_401(
        self, client: AsyncClient
    ) -> None:
        """TC-028b: Email não cadastrado deve retornar 401 (sem vazar info)."""
        response = await client.post(
            "/auth/login",
            data={
                "username": "naoexiste@test.com",
                "password": "Qualquer@123",
            },
        )
        assert response.status_code == 401


class TestAutorizacao:
    """TC-029 / TC-030 — RBAC e autenticação."""

    async def test_TC029_sem_token_retorna_401(self, client: AsyncClient) -> None:
        """TC-029: Acesso a endpoint protegido sem token deve retornar 401."""
        response = await client.get("/tutores")
        assert response.status_code == 401

    async def test_TC030_perfil_sem_permissao_retorna_403(
        self,
        client: AsyncClient,
        session: AsyncSession,
        tutor_ativo: Tutor,
    ) -> None:
        """
        TC-030: RBAC — usuário com perfil TUTOR tentando acessar
        POST /tutores (restrito a ADMIN/RECEPCIONISTA) deve retornar 403.
        """
        # Cria usuário com perfil TUTOR
        usuario_tutor = Usuario(
            nome="Tutor User",
            email="tutor_user@test.com",
            senha_hash=hash_password("Tutor@123456"),
            perfil=PerfilUsuario.TUTOR.value,
            tutor_id=tutor_ativo.id,
            ativo=True,
        )
        session.add(usuario_tutor)
        await session.flush()

        token_pair = create_token_pair(usuario_tutor.email, usuario_tutor.perfil)
        headers_tutor = {"Authorization": f"Bearer {token_pair.access_token}"}

        response = await client.post(
            "/tutores",
            json={
                "nome": "Tentativa Proibida",
                "cpf": "048.576.853-03",
                "email": "proibido@test.com",
                "telefone": "(11) 99999-9999",
            },
            headers=headers_tutor,
        )
        assert response.status_code == 403
        assert response.json()["error"] == "ACESSO_NEGADO"

    async def test_TC030b_veterinario_nao_pode_criar_tutor(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """TC-030b: VETERINARIO também não pode criar tutores."""
        from app.models.veterinario import Veterinario
        from app.models.enums import EspecialidadeVeterinario

        vet = Veterinario(
            nome="Dr. Vet",
            crmv="CRMV-RJ-99999",
            especialidade=EspecialidadeVeterinario.CLINICA_GERAL.value,
            ativo=True,
        )
        session.add(vet)
        await session.flush()

        usuario_vet = Usuario(
            nome="Vet User",
            email="vet_user@test.com",
            senha_hash=hash_password("Vet@123456"),
            perfil=PerfilUsuario.VETERINARIO.value,
            veterinario_id=vet.id,
            ativo=True,
        )
        session.add(usuario_vet)
        await session.flush()

        token_pair = create_token_pair(usuario_vet.email, usuario_vet.perfil)
        headers_vet = {"Authorization": f"Bearer {token_pair.access_token}"}

        response = await client.post(
            "/tutores",
            json={
                "nome": "Tentativa Vet",
                "cpf": "048.576.853-03",
                "email": "vet_tentativa@test.com",
                "telefone": "(21) 99999-9999",
            },
            headers=headers_vet,
        )
        assert response.status_code == 403


class TestRefreshToken:
    """TC-031 — Refresh token."""

    async def test_TC031_refresh_token_renova_tokens(
        self, client: AsyncClient, usuario_admin: Usuario
    ) -> None:
        """TC-031: Refresh token válido deve gerar novo par de tokens."""
        # Login para obter o par inicial
        resp_login = await client.post(
            "/auth/login",
            data={
                "username": usuario_admin.email,
                "password": "Admin@123456",
            },
        )
        assert resp_login.status_code == 200
        refresh_token = resp_login.json()["refresh_token"]

        # Usa o refresh token
        resp_refresh = await client.post(
            "/auth/refresh",
            params={"refresh_token": refresh_token},
        )
        assert resp_refresh.status_code == 200, resp_refresh.text
        body = resp_refresh.json()
        assert "access_token" in body
        assert "refresh_token" in body
        # Novos tokens devem ser diferentes dos originais
        assert body["access_token"] != resp_login.json()["access_token"]
